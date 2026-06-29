import json
import logging
import os
import time
import re
from typing import Any, Dict, List, Optional
from openai import OpenAI, RateLimitError, AuthenticationError

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


def _clean_json_response(text: str) -> str:
    """Cleans LLM response by stripping Markdown code blocks."""
    text = text.strip()
    if text.startswith("```"):
        # Handle ```json ... ``` or just ``` ... ```
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_unstructured_response(text: str) -> dict:
    """Dynamically extracts insight and recommendation from unstructured LLM text."""
    text_clean = text.strip()
    
    # Split by sentence endings (. ! ?)
    sentences_raw = re.split(r'(?<=[.!?])\s+', text_clean)
    sentences = []
    for s in sentences_raw:
        s_clean = s.replace("**", "").replace("*", "").strip()
        if s_clean:
            sentences.append(s_clean)
            
    insight = "LLM returned unstructured response."
    recommendation = "I am ready to assist you."
    
    if len(sentences) > 0:
        insight = sentences[0]
        
    recommendation_keywords = [
        "should", "recommend", "suggest", "need to", "must", 
        "order", "reorder", "prioritize", "check", "run", "monitor",
        "liquidate", "relocate", "mitigate", "action"
    ]
    
    found_rec = False
    for s in sentences[1:]:
        s_lower = s.lower()
        if any(kw in s_lower for kw in recommendation_keywords):
            recommendation = s
            found_rec = True
            break
            
    if not found_rec and len(sentences) > 1:
        recommendation = sentences[1]
        
    return {
        "answer": text_clean,
        "insight": insight,
        "recommendation": recommendation,
        "confidence": "low"
    }



def execute_tool(func_name: str, func_args: dict) -> dict:
    """Helper to execute local system tools based on LLM function calls."""
    try:
        if func_name == "get_forecast":
            from backend.copilot.tools import get_forecast_tool

            # Normalize arguments
            sku = func_args.get("sku")
            horizon = func_args.get("horizon", 30)
            return get_forecast_tool(sku, horizon)
        elif func_name == "get_inventory_health":
            from backend.copilot.tools import get_inventory_health_tool

            forecast = func_args.get("forecast")
            stock = func_args.get("stock")
            return get_inventory_health_tool(forecast, stock)
        elif func_name == "get_risk_ranking":
            from backend.copilot.tools import get_risk_ranking_tool

            products = func_args.get("products", [])
            return get_risk_ranking_tool(products)
        elif func_name == "run_simulation":
            from backend.copilot.tools import run_simulation_tool

            baseline = func_args.get("baseline_forecast")
            stock = func_args.get("stock")
            price = func_args.get("price")
            return run_simulation_tool(baseline, stock, price)
    except Exception as e:
        logger.error(f"Error executing tool {func_name}: {e}")
    return {}


class CircuitBreakerOpenError(RuntimeError):
    """Custom exception for when a circuit breaker is open."""

    pass


class LLMProvider:
    """Abstract base class for LLM Providers."""

    def chat(
        self,
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI API Provider."""

    _state = "CLOSED"
    _failures = 0
    _last_failure_time = 0
    _THRESHOLD = 3
    _TIMEOUT = 60  # seconds

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def chat(
        self,
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your-openai-key-here":
            logger.warning("OpenAI API key not set; skipping LLM call.")
            return {}

        # Circuit Breaker Logic
        now = time.time()
        if OpenAIProvider._state == "OPEN":
            if now - OpenAIProvider._last_failure_time > OpenAIProvider._TIMEOUT:
                logger.info("Circuit breaker HALF-OPEN: attempting recovery.")
                OpenAIProvider._state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError(
                    "Circuit breaker is OPEN. OpenAI API is currently throttled or unavailable."
                )


        try:
            client = OpenAI(api_key=self.api_key, timeout=30.0, max_retries=0)

            messages = [{"role": "system", "content": system_prompt}]
            if history:
                for msg in history[-10:]:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role in ["user", "assistant", "system"] and content:
                        messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": prompt})

            # Call OpenAI with tools
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                max_tokens=1000,
                temperature=0.0,
                timeout=25.0,
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # Handle tool calling loop
            if tool_calls and tools:
                messages.append(response_message)
                for tool_call in tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)
                    tool_res = execute_tool(func_name, func_args)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": func_name,
                            "content": json.dumps(tool_res),
                        }
                    )

                # Second call
                second_response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0.0, # Keep deterministic for final answer
                    timeout=25.0,
                )
                final_content = second_response.choices[0].message.content or ""
                final_content = final_content.strip()
            else:
                final_content = response_message.content or ""
                final_content = final_content.strip()

            # Reset circuit breaker on success
            OpenAIProvider._state = "CLOSED"
            OpenAIProvider._failures = 0
            try:
                # Clean and parse JSON
                return json.loads(_clean_json_response(final_content))
            except json.JSONDecodeError:
                logger.warning(
                    "OpenAI returned non-JSON content. Returning as raw answer."
                )
                return _parse_unstructured_response(final_content)

        except Exception as e:
            # Check for non-retriable exceptions to fast-open the circuit breaker
            is_non_retriable = isinstance(e, (RateLimitError, AuthenticationError)) or "quota" in str(e).lower()

            if is_non_retriable:
                OpenAIProvider._failures = OpenAIProvider._THRESHOLD
                OpenAIProvider._state = "OPEN"
                OpenAIProvider._last_failure_time = time.time()
                logger.error(
                    f"OpenAI non-retriable error encountered. Fast-opening circuit for {OpenAIProvider._TIMEOUT}s. Error: {e}"
                )
            else:
                OpenAIProvider._failures += 1
                if OpenAIProvider._failures >= OpenAIProvider._THRESHOLD:
                    logger.error(
                        f"OpenAI threshold reached. Opening circuit for {OpenAIProvider._TIMEOUT}s. Error: {e}"
                    )
                    OpenAIProvider._state = "OPEN"
                    OpenAIProvider._last_failure_time = time.time()
            raise e



class GroqProvider(LLMProvider):
    """Groq API Provider using direct HTTP request."""

    _state = "CLOSED"
    _failures = 0
    _last_failure_time = 0
    _THRESHOLD = 3
    _TIMEOUT = 60  # seconds

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    def chat(
        self,
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Groq API key is missing.")

        # Circuit Breaker Logic
        now = time.time()
        if GroqProvider._state == "OPEN":
            if now - GroqProvider._last_failure_time > GroqProvider._TIMEOUT:
                logger.info("Circuit breaker HALF-OPEN: attempting recovery for Groq.")
                GroqProvider._state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError(
                    "Circuit breaker is OPEN. Groq API is currently throttled or unavailable."
                )

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-10:]:
                role = msg.get("role")
                content = msg.get("content")
                if role in ["user", "assistant", "system"] and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 1000,
        }

        # Include tools in Groq payload
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Groq API returned error {response.status_code}: {response.text}"
                )

            res_data = response.json()
            choice = res_data["choices"][0]
            message_data = choice["message"]
            tool_calls = message_data.get("tool_calls")

            if tool_calls and tools:
                # Append assistant message with tool calls
                # Requests expects dict, not class
                messages.append(message_data)
                for tool_call in tool_calls:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"]["arguments"])
                    tool_res = execute_tool(func_name, func_args)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": func_name,
                            "content": json.dumps(tool_res),
                        }
                    )

                payload["messages"] = messages
                # Remove tools for the second call so the model is forced to reply with text
                if "tools" in payload:
                    del payload["tools"]
                if "tool_choice" in payload:
                    del payload["tool_choice"]

                second_response = requests.post(
                    url, headers=headers, json=payload, timeout=30
                )
                if second_response.status_code != 200:
                    raise RuntimeError(
                        f"Groq second call failed: {second_response.text}"
                    )
                msg_data = second_response.json()["choices"][0]["message"]
                final_content = msg_data.get("content") or ""
                final_content = final_content.strip()
            else:
                final_content = message_data.get("content") or ""
                final_content = final_content.strip()

            # Reset circuit breaker on success
            GroqProvider._state = "CLOSED"
            GroqProvider._failures = 0
            try:
                # Assume LLM returns JSON string
                return json.loads(_clean_json_response(final_content))
            except json.JSONDecodeError:
                logger.warning(
                    "Groq returned non-JSON content. Returning as raw answer."
                )
                return _parse_unstructured_response(final_content)

        except Exception as e:
            GroqProvider._failures += 1
            if GroqProvider._failures >= GroqProvider._THRESHOLD:
                logger.error(
                    f"Groq threshold reached. Opening circuit for {GroqProvider._TIMEOUT}s. Error: {e}"
                )
                GroqProvider._state = "OPEN"
                GroqProvider._last_failure_time = time.time()
            raise e


class OllamaProvider(LLMProvider):
    """Local Ollama Provider."""

    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")

    def chat(
        self,
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # Quick socket check to fail fast if host is unreachable
        import socket
        from urllib.parse import urlparse

        try:
            parsed_url = urlparse(self.host)
            host = parsed_url.hostname or "127.0.0.1"
            if host == "localhost":
                host = "127.0.0.1"
            port = parsed_url.port or 11434
            s = socket.create_connection((host, port), timeout=0.1)
            s.close()
        except Exception as e:
            raise RuntimeError(f"Ollama host {self.host} is unreachable: {e}")

        url = f"{self.host}/api/chat".replace("localhost", "127.0.0.1")

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for msg in history[-10:]:
                role = msg.get("role")
                content = msg.get("content")
                if role in ["user", "assistant", "system"] and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.0},
        }

        import httpx

        try:
            timeout_config = httpx.Timeout(90.0, connect=10.0, read=80.0)
            response = httpx.post(url, json=payload, timeout=timeout_config)
            if response.status_code != 200:
                raise RuntimeError(f"Ollama returned status {response.status_code}")
            res_data = response.json()
            final_content = res_data["message"]["content"].strip()
            try:
                # Assume LLM returns JSON string
                return json.loads(_clean_json_response(final_content))
            except json.JSONDecodeError:
                logger.warning(
                    "Ollama returned non-JSON content. Returning as raw answer."
                )
                return _parse_unstructured_response(final_content)
        except Exception as e:
            raise RuntimeError(f"Ollama connection failed: {e}")


class RuleBasedProvider(LLMProvider):
    """Local Rule Engine Fallback Provider."""

    def __init__(self, fallback_fn):
        self.fallback_fn = fallback_fn

    def chat(
        self,
        prompt: str,
        system_prompt: str,
        history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # Calls the passed local fallback function to generate structured rule-based response
        return self.fallback_fn()


class ProviderFactory:
    """Factory to create LLM providers."""

    @staticmethod
    def get_provider(provider_name: str, fallback_fn=None) -> LLMProvider:
        name = provider_name.strip().lower()
        if name == "openai":
            return OpenAIProvider()
        elif name == "groq":
            return GroqProvider()
        elif name == "ollama":
            return OllamaProvider()
        else:
            return RuleBasedProvider(fallback_fn)

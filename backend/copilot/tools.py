"""Tool definitions for the RetailGPT copilot (LangChain-compatible)."""

from __future__ import annotations

from typing import Dict


def get_forecast_tool(sku: str, horizon: int = 30) -> Dict:
    """Retrieve demand forecast for a SKU."""
    from backend.agents.forecast_agent import ForecastAgent

    agent = ForecastAgent()
    return agent.execute(sku=sku, horizon=horizon)


def get_inventory_health_tool(forecast: float, stock: float) -> Dict:
    """Calculate inventory health score and stockout risk."""
    from backend.inventory.optimizer import InventoryOptimizer

    optimizer = InventoryOptimizer()
    return {
        "health_score": optimizer.inventory_health_score(stock, forecast),
        "stockout_risk_pct": optimizer.stockout_probability(stock, forecast),
    }


def get_risk_ranking_tool(products: list) -> Dict:
    """Rank products by risk score."""
    from backend.risk.ranking import risk_engine

    return {"rankings": risk_engine.rank(products)}


def run_simulation_tool(baseline_forecast: float, stock: float, price: float) -> Dict:
    """Run a digital twin simulation with standard festival scenarios."""
    from backend.simulation.digital_twin import digital_twin

    return {
        "results": digital_twin.generate_festival_plan(baseline_forecast, stock, price)
    }


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get demand forecast for a SKU",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string", "description": "The SKU to get forecast for"},
                    "horizon": {"type": "integer", "description": "Forecast horizon (optional, default 30)"}
                },
                "required": ["sku"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_health",
            "description": "Check inventory health and stockout probability",
            "parameters": {
                "type": "object",
                "properties": {
                    "forecast": {"type": "number", "description": "Forecasted demand"},
                    "stock": {"type": "number", "description": "Current stock level"}
                },
                "required": ["forecast", "stock"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_ranking",
            "description": "Rank a portfolio of SKUs by risk",
            "parameters": {
                "type": "object",
                "properties": {
                    "products": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "forecast": {"type": "number"},
                                "stock": {"type": "number"},
                                "revenue": {"type": "number"}
                            },
                            "required": ["sku"]
                        },
                        "description": "List of products with their sku, forecast, stock, and revenue"
                    }
                },
                "required": ["products"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_simulation",
            "description": "Simulate demand scenarios using digital twin",
            "parameters": {
                "type": "object",
                "properties": {
                    "baseline_forecast": {"type": "number"},
                    "stock": {"type": "number"},
                    "price": {"type": "number"}
                },
                "required": ["baseline_forecast", "stock", "price"]
            }
        }
    }
]

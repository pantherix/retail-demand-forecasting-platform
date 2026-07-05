/* CopilotView – Fixed version */
"use client";

import { useState, useEffect } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { ErrorState } from "../ui/ErrorState";
import { useToast } from "../../hooks/useToast";
import {
  Sparkles,
  RefreshCw,
  Send,
  Loader2,
  Check,
  Settings,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export default function CopilotView() {
  const { triggerRefresh } = useStore();
  const { addToast } = useToast();

  const [queryInput, setQueryInput] = useState("");
  const [cards, setCards] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actioningSku, setActioningSku] = useState<string | null>(null);
  const [chatResponse, setChatResponse] = useState<any>(null);

  // Animated typing states
  const [animatedAnswer, setAnimatedAnswer] = useState("");
  const [animatedInsight, setAnimatedInsight] = useState("");
  const [animatedRecommendation, setAnimatedRecommendation] = useState("");

  // Collapsible settings
  const [showSettings, setShowSettings] = useState(false);
  const [provider, setProvider] = useState("openai");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(500);
  const [modelName, setModelName] = useState("");
  const [settingsReady, setSettingsReady] = useState(false);

  const selectedDatasetId = useStore((s) => s.selectedDatasetId);

  // Load persisted settings on mount – ensure defaults are written if missing
  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedProvider = localStorage.getItem("copilot_provider") || "openai";
      const storedTemp = parseFloat(localStorage.getItem("copilot_temperature") || "0.7");
      const storedMax = parseInt(localStorage.getItem("copilot_max_tokens") || "500", 10);
      const storedModel = localStorage.getItem("copilot_model") || "";

      setProvider(storedProvider);
      setTemperature(storedTemp);
      setMaxTokens(storedMax);
      setModelName(storedModel);
    }
    setSettingsReady(true);
  }, []);

  // Helper to persist a setting and update state
  const updateSetting = (key: string, val: any, setter: any) => {
    setter(val);
    try {
      localStorage.setItem(key, val.toString());
    } catch (e) {
      console.warn("Failed to persist copilot setting", key, e);
    }
  };

  const getSettingsPayload = () => ({
    provider,
    temperature,
    max_tokens: maxTokens,
    model: modelName || undefined,
    dataset_id: selectedDatasetId,
    history: [],
  });

  // Animate answer/insight/recommendation when chatResponse arrives
  useEffect(() => {
    if (!chatResponse) {
      setAnimatedAnswer("");
      setAnimatedInsight("");
      setAnimatedRecommendation("");
      return;
    }
    let cancelled = false;
    const animate = async () => {
      const animateText = async (txt: string, setter: (v: string) => void) => {
        if (!txt) return;
        const words = txt.split(" ");
        let cur = "";
        for (let i = 0; i < words.length; i++) {
          if (cancelled) return;
          cur += (i === 0 ? "" : " ") + words[i];
          setter(cur);
          await new Promise((r) => setTimeout(r, 15));
        }
      };
      setAnimatedAnswer("");
      setAnimatedInsight("");
      setAnimatedRecommendation("");
      await animateText(chatResponse.answer || "", setAnimatedAnswer);
      if (chatResponse.insight && chatResponse.insight !== chatResponse.answer) {
        await animateText(chatResponse.insight, setAnimatedInsight);
      }
      if (chatResponse.recommendation) {
        await animateText(chatResponse.recommendation, setAnimatedRecommendation);
      }
    };
    animate();
    return () => {
      cancelled = true;
    };
  }, [chatResponse]);

  const handleQuery = async (queryText: string) => {
    if (!queryText.trim() || isLoading) return;
    setIsLoading(true);
    setAnimatedAnswer("");
    setAnimatedInsight("");
    setAnimatedRecommendation("");
    try {
      console.log("Copilot query payload", { query: queryText, settings: getSettingsPayload() });
      const res = await api.copilotChat(queryText, getSettingsPayload());
      console.log("Copilot response", res);
      setChatResponse(res);
      const rawCards = res?.action_cards ?? res?.playbook_cards ?? [];
      setCards(Array.isArray(rawCards) ? rawCards : []);
      if (rawCards.length > 0) {
        addToast(`Copilot playbooks updated. Resolved ${rawCards.length} action proposals.`, "success");
      }
    } catch (err: any) {
      console.error("Copilot query error", err);
      setErrorMsg(err.message || err.detail || "Failed to process Copilot query.");
      addToast(err.message || "Failed to process Copilot query.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleExecutePlaybook = async (sku: string, qty: number, supplierId: number) => {
    if (actioningSku) return;
    setActioningSku(sku);
    addToast(`Executing playbook transaction for SKU ${sku}...`, "info");
    try {
      const res = await api.autogeneratePO({ sku, quantity: qty, supplier_id: supplierId || 1 });
      if (res.success) {
        addToast(`Emergency PO created successfully for ${qty} units of SKU ${sku}!`, "success");
        triggerRefresh();
        // Refresh the chat to remove resolved playbook
        const updated = await api.copilotChat(queryInput || "What should I order today?", getSettingsPayload());
        setChatResponse(updated);
        const raw = updated?.action_cards ?? updated?.playbook_cards ?? [];
        setCards(Array.isArray(raw) ? raw : []);
      } else {
        throw new Error("Write-back transaction was rejected by database engine.");
      }
    } catch (err: any) {
      console.error("Playbook execution error", err);
      addToast(err.message || "Playbook write-back transaction failed.", "error");
    } finally {
      setActioningSku(null);
    }
  };

  const formatCurrency = (val: number | undefined) =>
    (val ?? 0).toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

  const suggestions = ["What should I order today?", "Show stockouts for SKU-810", "Show replenishment playbooks"];

  return (
    <div className="bg-[#09090B] border border-[#27272A] rounded-xl p-8 space-y-8 text-zinc-100 font-sans shadow-2xl">
      {/* Header */}
      <div className="border-b border-[#27272A] pb-6 flex flex-col md:flex-row md:justify-between md:items-center gap-4">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[#DC2626]" /> COGNITIVE COMMANDER
          </h2>
          <p className="text-xs text-zinc-400 mt-1">Structured Query Router parses natural language intents into transactional playbooks.</p>
        </div>
      </div>

      {/* Settings Panel */}
      <div className="border border-[#27272A] rounded-lg bg-[#18181B] overflow-hidden">
        <button
          type="button"
          onClick={() => setShowSettings(!showSettings)}
          className="w-full px-5 py-3 flex justify-between items-center bg-[#18181B] text-xs font-mono font-bold uppercase tracking-wider text-zinc-400 hover:text-white transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings className="h-4 w-4 text-[#DC2626]" />
            <span>LLM Cockpit Settings</span>
          </div>
          {showSettings ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
        {showSettings && (
          <div className="px-5 pb-5 border-t border-[#27272A]/60 pt-4 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs font-mono">
            {/* Provider */}
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">LLM Provider</label>
              <select
                value={provider}
                onChange={(e) => updateSetting("copilot_provider", e.target.value, setProvider)}
                className="w-full px-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-zinc-200 focus:outline-none focus:border-[#DC2626] cursor-pointer"
              >
                <option value="openai">OpenAI (Default)</option>
                <option value="groq">Groq (High-Speed)</option>
                <option value="ollama">Ollama (Local LLM)</option>
                <option value="rule_based">Rule-Based Fallback</option>
              </select>
            </div>
            {/* Model Name */}
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">Model Name Override</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => updateSetting("copilot_model", e.target.value, setModelName)}
                placeholder="e.g. gpt-4o-mini"
                className="w-full px-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-[#DC2626]"
              />
            </div>
            {/* Temperature */}
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">Temperature</label>
                <span className="text-[10px] text-[#DC2626] font-bold">{temperature.toFixed(1)}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.1"
                value={temperature}
                onChange={(e) => updateSetting("copilot_temperature", Number(e.target.value), setTemperature)}
                className="w-full accent-[#DC2626] bg-[#09090B] border border-[#27272A] rounded cursor-pointer"
              />
            </div>
            {/* Max Tokens */}
            <div className="space-y-1.5">
              <label className="text-[10px] text-zinc-400 uppercase tracking-wider block">Max Tokens</label>
              <input
                type="number"
                value={maxTokens}
                onChange={(e) => updateSetting("copilot_max_tokens", Number(e.target.value), setMaxTokens)}
                className="w-full px-3 py-2 bg-[#09090B] border border-[#27272A] rounded text-zinc-200 focus:outline-none focus:border-[#DC2626]"
              />
            </div>
          </div>
        )}
      </div>

      {/* Query Bar */}
      <div className="space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleQuery(queryInput);
          }}
          className="flex gap-3"
        >
          <input
            type="text"
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Search inventory risks or ask: 'What should I order today?'"
            className="flex-1 px-4 py-2.5 bg-[#18181B] border border-[#27272A] rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-[#DC2626] font-mono shadow-inner"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !queryInput.trim()}
            className="px-6 bg-[#DC2626] hover:bg-[#B91C1C] text-white font-mono font-bold text-xs uppercase tracking-wider rounded-lg transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            <span>SCAN</span>
          </button>
        </form>
        {/* Suggestion prompts */}
        <div className="flex flex-wrap gap-2 pt-1">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setQueryInput(s);
                handleQuery(s);
              }}
              disabled={isLoading}
              className="text-[10px] font-mono bg-[#18181B] border border-[#27272A] hover:border-zinc-500 text-zinc-400 hover:text-white px-2.5 py-1 rounded transition-colors cursor-pointer disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* AI Response */}
      {errorMsg && <ErrorState message={errorMsg} onRetry={() => handleQuery(queryInput)} />}
      {chatResponse && !isLoading && (
        <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-4 w-4 text-[#DC2626]" />
            <h3 className="font-mono font-bold text-sm text-white uppercase">AI Analysis</h3>
          </div>
          {chatResponse.answer && (
            <p className="text-sm text-zinc-300 leading-relaxed font-sans">
              {animatedAnswer}
              {animatedAnswer !== chatResponse.answer && <span className="inline-block w-1.5 h-3.5 bg-[#DC2626] animate-pulse ml-1" />}
            </p>
          )}
          {chatResponse.insight && chatResponse.insight !== chatResponse.answer && animatedAnswer === chatResponse.answer && (
            <div className="mt-3 p-3 bg-[#09090B] border border-[#27272A] rounded-md border-l-2 border-l-[#DC2626] transition-all duration-300">
              <p className="text-xs text-zinc-450 font-mono">
                <span className="text-zinc-500 uppercase block mb-1 text-[10px]">Insight</span>
                {animatedInsight}
                {animatedInsight !== chatResponse.insight && <span className="inline-block w-1.5 h-3 bg-[#DC2626] animate-pulse ml-0.5" />}
              </p>
            </div>
          )}
          {chatResponse.recommendation && animatedAnswer === chatResponse.answer && (
            <div className="mt-3 p-3 bg-[#09090B] border border-[#27272A] rounded-md border-l-2 border-l-emerald-500 transition-all duration-300">
              <p className="text-xs text-zinc-450 font-mono">
                <span className="text-zinc-500 uppercase block mb-1 text-[10px]">Recommendation</span>
                {animatedRecommendation}
                {animatedRecommendation !== chatResponse.recommendation && (
                  <span className="inline-block w-1.5 h-3 bg-emerald-500 animate-pulse ml-0.5" />
                )}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Playbook Deck */}
      <div className="space-y-4 pt-4 border-t border-[#27272A]/50">
        <div className="flex justify-between items-center">
          <h3 className="text-xs font-mono font-bold tracking-widest text-[#DC2626] uppercase">Active Playbook Deck</h3>
          <span className="text-[10px] font-mono text-zinc-500">{cards.length} cards matched</span>
        </div>
        {/* Loading spinner */}
        {isLoading && (
          <div className="flex flex-col justify-center items-center py-12 space-y-3">
            <RefreshCw className="h-8 w-8 text-[#DC2626] animate-spin" />
            <p className="text-zinc-500 text-[10px] font-mono">ROUTING ACTION SCHEMA...</p>
          </div>
        )}
        {/* Action cards grid */}
        {!isLoading && (
          <>
            {cards.length === 0 ? (
              <div className="bg-[#18181B] border border-[#27272A] p-10 rounded-lg text-center space-y-2">
                <Check className="h-8 w-8 text-emerald-400 mx-auto" />
                <h4 className="font-bold text-xs text-white font-mono uppercase">All Operations Balanced</h4>
                <p className="text-[11px] text-zinc-500 max-w-xs mx-auto leading-relaxed">
                  No pending replenishment orders generated for this query segment.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {cards.map((card: any, idx: number) => {
                  const sku = card?.params?.sku ?? "N/A";
                  const quantity = card?.params?.quantity ?? 0;
                  const supplierId = card?.params?.supplier_id ?? 1;
                  const valueAtRisk = card?.params?.value_at_risk ?? 0;
                  const isActioning = actioningSku === sku;
                  return (
                    <div
                      key={`${sku}-${idx}`}
                      className="bg-[#18181B] border border-[#27272A] rounded-lg p-5 flex flex-col justify-between hover:border-[#DC2626]/40 transition-all relative shadow-sm"
                    >
                      <div className="space-y-4">
                        {/* Title & VaR */}
                        <div className="flex justify-between items-start gap-2">
                          <h4 className="font-bold text-sm text-white font-mono leading-tight">
                            {card?.title ?? "Emergency Replenishment Card"}
                          </h4>
                          <div className="text-right shrink-0">
                            <span className="text-[8px] font-mono text-zinc-400 block uppercase">VALUE-AT-RISK</span>
                            <span className="text-xs font-bold font-mono text-red-400">{formatCurrency(valueAtRisk)}</span>
                          </div>
                        </div>
                        {/* Description */}
                        <p className="text-xs text-zinc-400 leading-relaxed font-sans font-normal">
                          {card?.description ?? "Critical order proposal required to mitigate stocking gap."}
                        </p>
                        {/* Parameter Details */}
                        {card?.action !== "navigate" && sku !== "N/A" && (
                          <div className="p-3 bg-[#09090B] border border-[#27272A] rounded grid grid-cols-2 gap-3 text-[10px] font-mono">
                            <div>
                              <span className="text-zinc-500 block uppercase text-[8px]">TARGET SKU</span>
                              <span className="text-zinc-200">{sku}</span>
                            </div>
                            <div>
                              <span className="text-zinc-500 block uppercase text-[8px]">REORDER QUANTITY</span>
                              <span className="text-zinc-200">{quantity} Units</span>
                            </div>
                          </div>
                        )}
                        {/* Action button */}
                        {card?.action === "navigate" ? (
                          <button
                            onClick={() => {
                              if (card?.params?.path) {
                                window.location.href = card.params.path;
                              }
                            }}
                            className="mt-6 w-full py-2 bg-[#27272A] hover:bg-[#3F3F46] text-zinc-200 text-xs font-mono font-bold uppercase rounded transition-colors flex items-center justify-center gap-1.5"
                          >
                            Go to Reorder Engine
                          </button>
                        ) : (
                          <button
                            onClick={() => handleExecutePlaybook(sku, quantity, supplierId)}
                            disabled={isActioning}
                            className="mt-6 w-full py-2 bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-mono font-bold uppercase rounded cursor-pointer transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                          >
                            {isActioning ? (
                              <>
                                <Loader2 className="h-3.5 w-3.5 animate-spin" /> EXECUTING...
                              </>
                            ) : (
                              <>
                                <Check className="h-3.5 w-3.5" /> Approve Emergency PO
                              </>
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
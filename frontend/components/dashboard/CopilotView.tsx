import { useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { RefreshCw, Send } from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, PieChart, Pie, LineChart, Line
} from "recharts";

export default function CopilotView() {
  const { setActiveSku, setActiveTab } = useStore();
  const [messages, setMessages] = useState<Array<{ sender: "user" | "copilot"; text: string; data?: any }>>([
    { sender: "copilot", text: "Welcome to the RetailGPT Decision Copilot. Ask me questions like: 'What should I order today?' or 'Which SKU hurts revenue?'" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const predefinedQuestions = [
    "What should I order today?",
    "Which SKU is hurting revenue?",
    "Which products will stock out?",
    "Which inventory should be liquidated?"
  ];

  const currentSuggestions = useMemo(() => {
    // Traverse backwards to find the last copilot response that has suggestion chips
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === "copilot" && messages[i].data?.suggestions && messages[i].data.suggestions.length > 0) {
        return messages[i].data.suggestions;
      }
    }
    return predefinedQuestions;
  }, [messages]);

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;
    
    setMessages((prev) => [...prev, { sender: "user", text: textToSend }]);
    setInput("");
    setLoading(true);

    try {
      // Pass message and history
      const historyPayload = messages.map(m => ({
        role: m.sender === "user" ? "user" : "assistant",
        content: m.text
      }));
      const res = await api.copilotChat(textToSend, historyPayload);
      const copilotResponseText = `${res.insight}\n\n**Recommendation:** ${res.recommendation}`;
      setMessages((prev) => [...prev, { sender: "copilot", text: copilotResponseText, data: res }]);
    } catch (err: any) {
      setMessages((prev) => [...prev, { sender: "copilot", text: `Error processing query: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 flex flex-col h-[calc(100vh-14rem)]">
      {/* Quick Actions / Suggestions */}
      <div className="flex flex-wrap gap-2 justify-center py-2 shrink-0">
        {currentSuggestions.map((q: string, idx: number) => (
          <button
            key={idx}
            onClick={() => handleSend(q)}
            disabled={loading}
            className="px-3 py-1.5 rounded-full border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-350 dark:hover:border-zinc-700 text-zinc-650 dark:text-zinc-300 hover:text-zinc-950 dark:hover:text-zinc-50 text-xs font-mono font-medium transition-colors cursor-pointer disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Messages Window */}
      <div className="flex-1 min-h-0 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg p-6 overflow-y-auto space-y-6 shadow-sm">
        {messages.map((m, idx) => {
          const isUser = m.sender === "user";
          return (
            <div key={idx} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-xl rounded-lg p-5 border ${
                isUser 
                  ? "bg-zinc-50 dark:bg-zinc-950/40 border-zinc-200 dark:border-zinc-800 text-zinc-955 dark:text-zinc-50 font-sans font-medium" 
                  : "bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-850 text-zinc-955 dark:text-zinc-50 space-y-4 shadow-sm"
              }`}>
                <div className="flex items-center gap-2 mb-1.5 shrink-0">
                  <span className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider">
                    {isUser ? "Operator" : "RetailGPT Copilot"}
                  </span>
                </div>
                
                <div className="text-xs leading-relaxed whitespace-pre-wrap font-sans font-medium">
                  {m.text}
                </div>

                {!isUser && m.data && (
                  <div className="mt-4 pt-4 border-t border-zinc-150 dark:border-zinc-800 space-y-4">
                    {/* Financial Exposure card */}
                    {m.data.financial_impact && m.data.financial_impact !== "N/A" && (
                      <div className="p-3 bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-850 rounded flex justify-between items-center">
                        <span className="text-[10px] font-mono font-bold text-zinc-500 dark:text-zinc-400 uppercase">Financial Exposure</span>
                        <span className="text-xs font-mono font-bold text-red-600 dark:text-red-400">{m.data.financial_impact}</span>
                      </div>
                    )}

                    {/* Table payload rendering */}
                    {m.data.table && (
                      <div className="border border-zinc-200 dark:border-zinc-800 rounded-lg overflow-x-auto text-[10px] font-sans">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="bg-zinc-50 dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 font-mono text-[9px] uppercase tracking-wider text-zinc-500">
                              {m.data.table.headers.map((h: string, idx: number) => (
                                <th key={idx} className="py-2 px-3 font-bold">{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800 text-zinc-750 dark:text-zinc-300">
                            {m.data.table.rows.map((row: string[], ri: number) => (
                              <tr key={ri} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/10">
                                {row.map((val: string, ci: number) => (
                                  <td key={ci} className="py-2 px-3">{val}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Chart payload rendering */}
                    {m.data.chart && m.data.chart.data && m.data.chart.data.length > 0 && (
                      <div className="h-44 w-full mt-3 font-mono">
                        {m.data.chart.type === "bar" ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={m.data.chart.data} margin={{ top: 10, right: 10, left: -25, bottom: 5 }}>
                              <XAxis dataKey="name" fontSize={8} tickLine={false} />
                              <YAxis fontSize={8} tickLine={false} />
                              <RechartsTooltip contentStyle={{ fontSize: 9 }} />
                              <Bar dataKey="value" fill="#27272a" radius={[3, 3, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        ) : m.data.chart.type === "line" ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={m.data.chart.data} margin={{ top: 10, right: 10, left: -25, bottom: 5 }}>
                              <XAxis dataKey="name" fontSize={8} tickLine={false} />
                              <YAxis fontSize={8} tickLine={false} />
                              <RechartsTooltip contentStyle={{ fontSize: 9 }} />
                              <Line type="monotone" dataKey="value" stroke="#27272a" strokeWidth={1.5} dot={{ r: 2 }} />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : m.data.chart.type === "pie" ? (
                          <div className="h-full w-full flex items-center justify-center">
                            <ResponsiveContainer width="100%" height="100%">
                              <PieChart>
                                <Pie
                                  data={m.data.chart.data}
                                  dataKey="value"
                                  nameKey="name"
                                  cx="50%"
                                  cy="50%"
                                  outerRadius={45}
                                  fill="#27272a"
                                  label={{ fontSize: 7 }}
                                />
                                <RechartsTooltip contentStyle={{ fontSize: 9 }} />
                              </PieChart>
                            </ResponsiveContainer>
                          </div>
                        ) : null}
                      </div>
                    )}

                    {/* Action Cards rendering */}
                    {m.data.action_cards && m.data.action_cards.length > 0 && (
                      <div className="space-y-2">
                        {m.data.action_cards.map((card: any, idx: number) => (
                          <div key={idx} className="bg-zinc-50 dark:bg-zinc-950/40 border border-zinc-200 dark:border-zinc-800 p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
                            <div className="space-y-0.5">
                              <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-50">{card.title}</h4>
                              <p className="text-[10px] text-zinc-500 dark:text-zinc-400">{card.description}</p>
                            </div>
                            <button
                              onClick={() => {
                                if (card.action === "navigate") {
                                  const path = card.params?.path;
                                  const sku = card.params?.sku;
                                  if (sku) setActiveSku(sku);
                                  if (path === "/product-intelligence") {
                                    setActiveTab("product-intelligence");
                                  } else if (path === "/decisions" || path === "/action-center") {
                                    setActiveTab("action-center");
                                  } else if (path === "/reorder") {
                                    setActiveTab("reorder");
                                  } else if (path === "/warehouses") {
                                    setActiveTab("warehouses");
                                  } else if (path === "/scenario-lab") {
                                    setActiveTab("scenario-lab");
                                  }
                                }
                              }}
                              className="px-2.5 py-1.5 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 dark:text-zinc-900 text-white font-mono font-bold rounded cursor-pointer transition-all uppercase text-[9px] self-end sm:self-center"
                            >
                              Execute
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* SKU Link Drilldown fallback if raw sku matches */}
                    {m.data.sku && (!m.data.action_cards || m.data.action_cards.length === 0) && (
                      <div className="flex justify-between items-center gap-4 text-[10px]">
                        <span className="text-zinc-400 dark:text-zinc-500 font-mono">Entity Link: <strong className="text-zinc-700 dark:text-zinc-300">{m.data.sku}</strong></span>
                        <button 
                          onClick={() => {
                            setActiveSku(m.data.sku);
                            setActiveTab("product-intelligence");
                          }}
                          className="px-2.5 py-1 bg-zinc-955 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-950 text-white font-mono font-bold rounded cursor-pointer transition-all uppercase text-[9px]"
                        >
                          View SKU Intel
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-zinc-55 dark:bg-zinc-950/40 border border-zinc-150 dark:border-zinc-850 rounded-lg p-5 space-y-2 max-w-sm">
              <span className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-wider block">RetailGPT Copilot</span>
              <div className="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-mono">
                <RefreshCw className="h-3.5 w-3.5 animate-spin text-zinc-400" />
                <span>Simulating decision trees...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input controls */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend(input);
        }}
        className="flex gap-3 shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 px-4 py-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm text-zinc-900 dark:text-zinc-105 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none focus:border-zinc-950 dark:focus:border-zinc-50 font-sans shadow-sm"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-6 bg-zinc-950 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-955 text-white font-mono font-bold text-xs uppercase tracking-wider rounded-lg transition-colors cursor-pointer shadow-sm disabled:opacity-50 flex items-center gap-1.5"
        >
          <Send className="h-3.5 w-3.5" />
          <span>Send</span>
        </button>
      </form>
    </div>
  );
}

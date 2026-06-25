import React, { memo, useState, useMemo, useEffect } from "react";
import { Sparkles, DollarSign, Activity, Percent, ArrowUpRight, Check, X, ShieldAlert, ArrowRight } from "lucide-react";
import { DecisionItem } from "./DecisionQueue";
import { useToast } from "../../hooks/useToast";

interface AIReasoningConsoleProps {
  decision: DecisionItem | null;
  onApprove: (id: number, qty: number) => void;
  onReject: (id: number) => void;
  onModify: (id: number, qty: number) => void;
  onEscalate: (id: number, role: string) => void;
  onAddNote: (sku: string, note: string) => Promise<void>;
  currentUserId: string;
}

export const AIReasoningConsole: React.FC<AIReasoningConsoleProps> = memo(
  ({ decision, onApprove, onReject, onModify, onEscalate, onAddNote, currentUserId }) => {
    const { addToast } = useToast();
    const [isModifying, setIsModifying] = useState(false);
    const [modifiedQty, setModifiedQty] = useState(0);
    const [isEscalating, setIsEscalating] = useState(false);
    const [escalateRole, setEscalateRole] = useState("manager");
    const [noteText, setNoteText] = useState("");
    const [isSavingNote, setIsSavingNote] = useState(false);

    // Synchronize modifying quantity when selected decision changes
    useEffect(() => {
      if (decision) {
        setModifiedQty(decision.reorder_quantity);
        setIsModifying(false);
        setIsEscalating(false);
        setNoteText("");

        if (!decision.supplier_id && decision.reorder_quantity > 0) {
          addToast(`SKU ${decision.sku} is missing a supplier configuration. Approval is locked.`, "error");
        }
      }
    }, [decision]);

    // Calculate dynamic metrics using useMemo
    const financialMetrics = useMemo(() => {
      if (!decision) return null;

      const revenueProtected = decision.revenue_protected ?? decision.revenueProtected ?? decision.revenue_impact ?? 0;
      const revenueAtRisk = decision.revenue_at_risk ?? decision.revenueAtRisk ?? decision.revenue_impact ?? 0;
      const costOfAction = decision.cost_of_action ?? decision.costOfAction ?? Math.max(0, revenueProtected - (decision.profit_impact ?? 0));
      const profitImpact = decision.profit_impact ?? 0;
      const roi = costOfAction > 0 ? (profitImpact / costOfAction) * 100 : 0;

      return {
        protectedRevenue: revenueProtected,
        revenueAtRisk: revenueAtRisk,
        costOfAction: Math.max(0, costOfAction),
        roi: Math.round(roi),
      };
    }, [decision]);

    // AI Reasoning sentences
    const aiReasoning = useMemo(() => {
      if (!decision) return [];
      const days = decision.days_remaining;
      const revenue = decision.revenue_impact;
      const confidence = decision.confidence_score;
      const velocity = decision.reorder_quantity > 0 ? Math.round(decision.reorder_quantity / 15) : 10;

      return [
        `Demand is projected to average ${velocity} units daily, creating localized stockout warnings.`,
        `Current inventory covers only ${days} days, representing high vulnerability relative to supplier lead time.`,
        `Expected revenue loss is ₹${revenue.toLocaleString()} if replenishment is not executed.`,
        `Replenishment suggestions are built under a ${confidence}% historical confidence threshold.`,
      ];
    }, [decision]);

    if (!decision) {
      return (
        <div className="bg-[#111114] border border-zinc-800 p-6 rounded-xl shadow-sm h-[650px] flex items-center justify-center text-zinc-400 font-mono text-xs italic">
          Select a decision from the queue to load AI reasoning panel.
        </div>
      );
    }

    const handleSaveNote = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!noteText.trim()) return;
      setIsSavingNote(true);
      try {
        await onAddNote(decision.sku, noteText);
        setNoteText("");
        addToast("Comment successfully saved to decision logs.", "success");
      } catch (err: any) {
        addToast(err.message || "Failed to save comment", "error");
      } finally {
        setIsSavingNote(false);
      }
    };

    const handleModifySubmit = () => {
      onModify(decision.id, modifiedQty);
      setIsModifying(false);
    };

    const handleEscalateSubmit = () => {
      onEscalate(decision.id, escalateRole);
      setIsEscalating(false);
    };

    return (
      <div 
        className="backdrop-blur-md bg-white/70 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/60 p-6 rounded-xl shadow-sm flex flex-col h-[650px] space-y-4 overflow-y-auto"
        role="region"
        aria-label="AI Decision Spotlight Console"
      >
        {/* Header */}
        <div className="flex justify-between items-start gap-4 border-b border-zinc-800 pb-3 shrink-0">
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-wider block">
              Spotlight Decision • {decision.category}
            </span>
            <h3 className="text-lg tracking-tight font-extrabold text-zinc-900 dark:text-zinc-50">
              {decision.sku} - {decision.product_name}
            </h3>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase">Assigned To</span>
            <p className="text-xs font-mono font-bold text-white mt-0.5">{decision.owner}</p>
          </div>
        </div>

        {/* AI Reasoning Panel */}
        <div className="bg-indigo-50/40 dark:bg-indigo-950/10 border border-indigo-100 dark:border-indigo-900/40 p-4 rounded-xl space-y-3 shrink-0">
          <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-indigo-950 dark:text-indigo-300 flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            AI Reasoning & Analysis
          </h4>
          <ul className="space-y-2 text-xs text-zinc-600 dark:text-zinc-400 font-sans leading-relaxed font-medium list-disc pl-4">
            {aiReasoning.map((reason, idx) => (
              <li key={idx}>{reason}</li>
            ))}
          </ul>
        </div>

        {/* Financial Impact Grid */}
        {financialMetrics && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 shrink-0">
            {/* Protected Revenue */}
            <div className="bg-zinc-900/40 border border-zinc-150 dark:border-zinc-800 p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[9px] font-mono font-bold text-zinc-400 uppercase tracking-wider">Protected</span>
              <h5 className="text-sm font-extrabold text-emerald-700 dark:text-emerald-400 mt-1">
                ₹{financialMetrics.protectedRevenue.toLocaleString()}
              </h5>
            </div>

            {/* Revenue At Risk */}
            <div className="bg-zinc-900/40 border border-zinc-150 dark:border-zinc-800 p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[9px] font-mono font-bold text-zinc-400 uppercase tracking-wider">At Risk</span>
              <h5 className="text-sm font-extrabold text-rose-700 dark:text-rose-400 mt-1">
                ₹{financialMetrics.revenueAtRisk.toLocaleString()}
              </h5>
            </div>

            {/* Cost of Action */}
            <div className="bg-zinc-900/40 border border-zinc-150 dark:border-zinc-800 p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[9px] font-mono font-bold text-zinc-400 uppercase tracking-wider">Cost of Action</span>
              <h5 className="text-sm font-extrabold text-white mt-1">
                ₹{financialMetrics.costOfAction.toLocaleString()}
              </h5>
            </div>

            {/* ROI */}
            <div className="bg-zinc-900/40 border border-zinc-150 dark:border-zinc-800 p-3 rounded-lg flex flex-col justify-between">
              <span className="text-[9px] font-mono font-bold text-zinc-400 uppercase tracking-wider">Margin ROI</span>
              <h5 className="text-sm font-extrabold text-indigo-700 dark:text-indigo-400 mt-1">
                {financialMetrics.roi}%
              </h5>
            </div>
          </div>
        )}

        {/* Resolution Actions */}
        <div className="border-t border-zinc-800 pt-3 shrink-0">
          {isModifying ? (
            /* Modification State */
            <div className="space-y-3 p-4 bg-zinc-900/40 border border-zinc-800 rounded-xl">
              <h4 className="text-xs font-mono font-bold uppercase text-zinc-700 dark:text-zinc-300">Modify Order Quantity</h4>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={modifiedQty}
                  onChange={(e) => setModifiedQty(Number(e.target.value))}
                  className="bg-white border border-zinc-200 text-xs rounded p-2 focus:outline-none w-28 font-mono font-bold"
                  aria-label="Modified reorder quantity"
                />
                <button
                  onClick={handleModifySubmit}
                  className="px-4 py-2 bg-zinc-950 text-white font-mono text-[10px] uppercase font-bold rounded flex items-center gap-1 shadow-sm hover:shadow"
                >
                  <Check className="h-3 w-3" /> Save
                </button>
                <button
                  onClick={() => setIsModifying(false)}
                  className="px-4 py-2 bg-zinc-200 text-zinc-600 font-mono text-[10px] uppercase font-bold rounded flex items-center gap-1"
                >
                  <X className="h-3 w-3" /> Cancel
                </button>
              </div>
            </div>
          ) : isEscalating ? (
            /* Escalation State */
            <div className="space-y-3 p-4 bg-zinc-900/40 border border-zinc-800 rounded-xl">
              <h4 className="text-xs font-mono font-bold uppercase text-zinc-700 dark:text-zinc-300">Escalate Decision To</h4>
              <div className="flex gap-2">
                <select
                  value={escalateRole}
                  onChange={(e) => setEscalateRole(e.target.value)}
                  className="bg-white border border-zinc-200 text-xs rounded p-2 focus:outline-none w-32 font-mono"
                  aria-label="Escalation target user role"
                >
                  <option value="manager">Manager</option>
                  <option value="director">Director</option>
                  <option value="admin">System Admin</option>
                </select>
                <button
                  onClick={handleEscalateSubmit}
                  className="px-4 py-2 bg-zinc-950 text-white font-mono text-[10px] uppercase font-bold rounded flex items-center gap-1 shadow-sm hover:shadow"
                >
                  <ArrowRight className="h-3 w-3" /> Escalate
                </button>
                <button
                  onClick={() => setIsEscalating(false)}
                  className="px-4 py-2 bg-zinc-200 text-zinc-600 font-mono text-[10px] uppercase font-bold rounded flex items-center gap-1"
                >
                  <X className="h-3 w-3" /> Cancel
                </button>
              </div>
            </div>
          ) : (
            /* Standard Buttons */
            <div className="space-y-3">
              {(!decision.supplier_id && decision.reorder_quantity > 0) && (
                <div className="bg-amber-955/20 border border-amber-900/50 p-3 rounded-lg flex items-center gap-2 text-amber-400 text-xs font-mono">
                  <ShieldAlert className="h-4 w-4 shrink-0 text-[#F59E0B]" />
                  <span>Supplier relationship missing. PO creation prevented. Please configure a supplier first.</span>
                </div>
              )}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <button
                  onClick={() => {
                    if (!decision.supplier_id && decision.reorder_quantity > 0) {
                      addToast("Supplier relationship missing. PO creation prevented.", "error");
                      return;
                    }
                    onApprove(decision.id, decision.reorder_quantity);
                  }}
                  disabled={!decision.supplier_id && decision.reorder_quantity > 0}
                  className={`py-2.5 font-mono text-[10px] uppercase font-bold tracking-wider rounded-lg transition-colors shadow-sm focus:outline-none focus:ring-1 ${
                    (!decision.supplier_id && decision.reorder_quantity > 0)
                      ? "bg-zinc-800 text-zinc-500 border border-zinc-700 cursor-not-allowed opacity-50"
                      : "bg-zinc-950 hover:bg-zinc-800 text-white dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] cursor-pointer focus:ring-zinc-950"
                  }`}
                  title={(!decision.supplier_id && decision.reorder_quantity > 0) ? "Supplier relationship missing" : "Approve and execute PO"}
                  aria-label={(!decision.supplier_id && decision.reorder_quantity > 0) ? "Supplier relationship missing" : "Approve and execute PO"}
                >
                  Approve
                </button>
                <button
                  onClick={() => onReject(decision.id)}
                  className="py-2.5 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 dark:bg-[#18181B] dark:hover:bg-zinc-800/50 dark:text-zinc-100 dark:border-[#27272A] font-mono text-[10px] uppercase font-bold tracking-wider rounded-lg cursor-pointer transition-colors"
                  aria-label="Reject recommendation"
                >
                  Reject
                </button>
                <button
                  onClick={() => setIsModifying(true)}
                  className="py-2.5 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 dark:bg-[#18181B] dark:hover:bg-zinc-800/50 dark:text-zinc-100 dark:border-[#27272A] font-mono text-[10px] uppercase font-bold tracking-wider rounded-lg cursor-pointer transition-colors"
                  aria-label="Modify reorder quantity"
                >
                  Modify
                </button>
                <button
                  onClick={() => setIsEscalating(true)}
                  className="py-2.5 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 dark:bg-[#18181B] dark:hover:bg-zinc-800/50 dark:text-zinc-100 dark:border-[#27272A] font-mono text-[10px] uppercase font-bold tracking-wider rounded-lg cursor-pointer transition-colors"
                  aria-label="Escalate ownership"
                >
                  Escalate
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Comment Box */}
        <form onSubmit={handleSaveNote} className="border-t border-zinc-800 pt-3 flex flex-col space-y-2 shrink-0">
          <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase">
            Resolution Comments Audit
          </span>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add audit comment..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              className="flex-1 bg-zinc-900 border border-zinc-800 text-xs rounded-lg p-2 focus:outline-none"
              aria-label="Add audit note comment text"
            />
            <button
              type="submit"
              disabled={isSavingNote || !noteText.trim()}
              className="px-4 bg-zinc-950 hover:bg-zinc-800 text-white font-mono text-[10px] uppercase font-bold rounded-lg cursor-pointer disabled:opacity-40"
            >
              Add Note
            </button>
          </div>
        </form>
      </div>
    );
  }
);

AIReasoningConsole.displayName = "AIReasoningConsole";

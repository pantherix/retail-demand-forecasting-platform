import React, { memo } from "react";
import { AlertCircle, ArrowRightLeft, ShoppingCart, TrendingDown } from "lucide-react";

export interface CriticalActionItem {
  sku: string;
  name: string;
  type: "reorder" | "transfer" | "liquidate";
  riskLevel: "critical" | "high" | "medium";
  revenueImpact: number;
  confidenceScore: number;
  recommendedAction: string;
  qty: number;
  rawItem: any;
}

interface CriticalActionsTableProps {
  actions: CriticalActionItem[];
  onApprove: (item: CriticalActionItem) => void;
  onInvestigate: (sku: string) => void;
  isUnavailable: boolean;
}

export const CriticalActionsTable: React.FC<CriticalActionsTableProps> = memo(
  ({ actions, onApprove, onInvestigate, isUnavailable }) => {

    const riskBadgeColors = {
      critical: "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-950/30 dark:border-rose-900/50 dark:text-rose-400",
      high: "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30 dark:border-amber-900/50 dark:text-amber-400",
      medium: "bg-zinc-50 border-zinc-200 text-zinc-700 dark:bg-zinc-900/30 dark:border-zinc-800 dark:text-zinc-400",
    };

    const actionIcons = {
      reorder: <ShoppingCart className="h-3.5 w-3.5 text-rose-600 dark:text-rose-400" />,
      transfer: <ArrowRightLeft className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />,
      liquidate: <TrendingDown className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />,
    };

    return (
    <div
      className="ferrari-panel p-6 space-y-4 relative overflow-hidden"
      role="region"
      aria-label="Critical Actions Inventory Decisional Table"
    >
      {/* Ambient soft glow */}
      <div className="absolute -top-24 -left-24 w-64 h-64 bg-[#E10600]/5 rounded-full blur-[100px] pointer-events-none" />
      {/* Glossy reflection layer */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />

      <div className="space-y-1 relative z-10">
        <span className="text-[10px] font-mono font-black text-[#FFDC00] uppercase tracking-widest block">
          Operational Backlog
        </span>
        <h3 className="text-lg font-black text-white tracking-tight">
          Critical Actions & Resolutions
        </h3>
      </div>

      {isUnavailable ? (
        <div className="py-8 text-center text-zinc-400 font-mono italic text-xs relative z-10">
          Data currently unavailable
        </div>
      ) : actions.length === 0 ? (
        <div className="py-8 border border-dashed border-white/10 rounded-lg text-center text-zinc-400 font-mono text-xs relative z-10">
          All inventory nodes balanced. No critical alerts.
        </div>
      ) : (
        <div className="overflow-x-auto border border-white/5 rounded-lg relative z-10">
          <table className="w-full text-left border-collapse font-mono text-xs hardware-table">
            <thead>
              <tr className="bg-white/5 border-b border-white/10 font-mono text-[9px] uppercase tracking-wider text-zinc-400">
                <th className="py-3 px-4 font-bold">SKU / Item</th>
                <th className="py-3 px-4 font-bold">Priority</th>
                <th className="py-3 px-4 font-bold text-right">Revenue Impact</th>
                <th className="py-3 px-4 font-bold text-center">Confidence</th>
                <th className="py-3 px-4 font-bold">Resolution Action</th>
                <th className="py-3 px-4 font-bold text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-zinc-300">
              {actions.map((item, idx) => {
                const isSupplierMissing = item.type === "reorder" && item.rawItem && !item.rawItem.supplier_id;
                return (
                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col gap-0.5">
                        <button
                          onClick={() => onInvestigate(item.sku)}
                          className="font-mono font-bold text-white hover:underline text-left cursor-pointer focus:outline-none rounded px-0.5"
                          aria-label={`Investigate details for SKU ${item.sku}`}
                        >
                          {item.sku}
                        </button>
                        <span className="text-[10px] text-zinc-500 font-medium truncate max-w-[150px]">
                          {item.name}
                        </span>
                        {isSupplierMissing && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-955/30 text-amber-400 border border-amber-900/50 text-[8px] font-mono font-bold uppercase mt-1 w-max cursor-help" title="Supplier relationship missing">
                            ⚠️ No Supplier
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full border text-[9px] font-mono font-extrabold uppercase ${riskBadgeColors[item.riskLevel]}`}>
                        {item.riskLevel}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-black text-rose-500 text-shadow-[0_0_6px_rgba(244,63,94,0.3)]">
                      ₹{item.revenueImpact.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-bold text-emerald-400 text-shadow-[0_0_6px_rgba(52,211,153,0.3)]">
                      {item.confidenceScore}%
                    </td>
                    <td className="py-3.5 px-4 font-medium">
                      <div className="flex items-center gap-1.5">
                        <div className="shrink-0 p-1 rounded bg-[#18181b] border border-white/5 shadow-sm">
                          {actionIcons[item.type]}
                        </div>
                        <span className="text-zinc-300">{item.recommendedAction}</span>
                      </div>
                    </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center justify-center gap-2">
                          <button
                            onClick={() => !isSupplierMissing && onApprove(item)}
                            disabled={isSupplierMissing}
                            className={`px-2.5 py-1 text-white font-mono text-[9px] uppercase font-extrabold tracking-wider rounded shadow-sm hover:shadow transition-all active:translate-y-0.5 focus:outline-none focus:ring-1 focus:ring-offset-1 ${isSupplierMissing
                                ? "bg-zinc-800 text-zinc-500 border border-zinc-700 cursor-not-allowed opacity-50"
                                : "bg-zinc-950 hover:bg-zinc-800 dark:bg-[#DC2626] dark:hover:bg-[#B91C1C] cursor-pointer focus:ring-zinc-950"
                              }`}
                            title={isSupplierMissing ? "Supplier relationship missing" : `Approve recommended action for SKU ${item.sku}`}
                            aria-label={isSupplierMissing ? "Supplier relationship missing" : `Approve recommended action for SKU ${item.sku}`}
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => onInvestigate(item.sku)}
                            className="px-2.5 py-1 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 hover:text-zinc-900 dark:bg-[#18181B] dark:hover:bg-zinc-800/50 dark:text-zinc-100 dark:border-[#27272A] font-mono text-[9px] uppercase font-extrabold tracking-wider rounded cursor-pointer transition-all focus:outline-none focus:ring-1 focus:ring-zinc-300"
                            aria-label={`Investigate SKU ${item.sku}`}
                          >
                            Investigate
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }
);

CriticalActionsTable.displayName = "CriticalActionsTable";

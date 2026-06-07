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
        className="bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-sm p-6 space-y-4"
        role="region"
        aria-label="Critical Actions Inventory Decisional Table"
      >
        <div className="space-y-1">
          <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
            Operational Backlog
          </span>
          <h3 className="text-lg font-bold text-zinc-900 dark:text-white tracking-tight">
            Critical Actions & Resolutions
          </h3>
        </div>

        {isUnavailable ? (
          <div className="py-8 text-center text-zinc-400 font-mono italic text-xs">
            Data currently unavailable
          </div>
        ) : actions.length === 0 ? (
          <div className="py-8 border border-dashed border-zinc-200 dark:border-zinc-800 rounded-lg text-center text-zinc-400 font-mono text-xs">
            All inventory nodes balanced. No critical alerts.
          </div>
        ) : (
          <div className="overflow-x-auto border border-zinc-100 dark:border-zinc-800/80 rounded-lg">
            <table className="w-full text-left border-collapse text-xs font-sans">
              <thead>
                <tr className="bg-zinc-50 dark:bg-zinc-900/50 border-b border-zinc-100 dark:border-zinc-800/80 font-mono text-[9px] uppercase tracking-wider text-zinc-500">
                  <th className="py-3 px-4 font-bold">SKU / Item</th>
                  <th className="py-3 px-4 font-bold">Priority</th>
                  <th className="py-3 px-4 font-bold text-right">Revenue Impact</th>
                  <th className="py-3 px-4 font-bold text-center">Confidence</th>
                  <th className="py-3 px-4 font-bold">Resolution Action</th>
                  <th className="py-3 px-4 font-bold text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/80 text-zinc-700 dark:text-zinc-300">
                {actions.map((item, idx) => (
                  <tr key={idx} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/20 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex flex-col gap-0.5">
                        <button
                          onClick={() => onInvestigate(item.sku)}
                          className="font-mono font-bold text-zinc-900 dark:text-white hover:underline text-left cursor-pointer focus:outline-none focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white rounded px-0.5"
                          aria-label={`Investigate details for SKU ${item.sku}`}
                        >
                          {item.sku}
                        </button>
                        <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-medium truncate max-w-[150px]">
                          {item.name}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded-full border text-[9px] font-mono font-extrabold uppercase ${riskBadgeColors[item.riskLevel]}`}>
                        {item.riskLevel}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right font-mono font-bold text-zinc-900 dark:text-white">
                      ₹{item.revenueImpact.toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-center font-mono font-medium">
                      {item.confidenceScore}%
                    </td>
                    <td className="py-3.5 px-4 font-medium">
                      <div className="flex items-center gap-1.5">
                        <div className="shrink-0 p-1 rounded bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/50 dark:border-zinc-700/50 shadow-sm">
                          {actionIcons[item.type]}
                        </div>
                        <span className="text-zinc-600 dark:text-zinc-400">{item.recommendedAction}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <button
                          onClick={() => onApprove(item)}
                          className="px-2.5 py-1 bg-zinc-950 hover:bg-zinc-800 text-white font-mono text-[9px] uppercase font-extrabold tracking-wider rounded shadow-sm hover:shadow cursor-pointer transition-all active:translate-y-0.5 focus:outline-none focus:ring-1 focus:ring-offset-1 focus:ring-zinc-950"
                          aria-label={`Approve recommended action for SKU ${item.sku}`}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => onInvestigate(item.sku)}
                          className="px-2.5 py-1 bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-700 hover:text-zinc-900 font-mono text-[9px] uppercase font-extrabold tracking-wider rounded cursor-pointer transition-all focus:outline-none focus:ring-1 focus:ring-zinc-300"
                          aria-label={`Investigate SKU ${item.sku}`}
                        >
                          Investigate
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    );
  }
);

CriticalActionsTable.displayName = "CriticalActionsTable";

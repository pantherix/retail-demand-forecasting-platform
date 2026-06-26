import React from "react";

export interface DecisionItem {
  sku: string;
  product_name: string;
  issue: string;
  revenue_protected?: number;
  revenue_at_risk?: number;
  cost_of_action?: number;
  status: string;
  owner: string;
  revenueProtected?: number;
  revenueAtRisk?: number;
  costOfAction?: number;
}

interface DecisionCardProps {
  item: DecisionItem;
  onExecute?: () => void;
  onSkuClick?: () => void;
}

export const DecisionCard: React.FC<DecisionCardProps> = ({ item, onExecute, onSkuClick }) => {
  const revenue_protected = item.revenue_protected ?? item.revenueProtected ?? 0;
  const revenue_at_risk = item.revenue_at_risk ?? item.revenueAtRisk ?? 0;
  const cost_of_action = item.cost_of_action ?? item.costOfAction ?? 0;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 rounded-lg space-y-3 shadow-sm">
      <div className="flex justify-between items-start">
        <button onClick={onSkuClick} className="font-mono text-xs font-bold underline">
          {item.sku}
        </button>
        <span className="text-sm font-mono font-bold">₹{revenue_at_risk.toLocaleString()}</span>
      </div>
      <div>
        <h3 className="text-base font-bold">{item.product_name}</h3>
        <p className="text-xs text-zinc-550">{item.issue}</p>
      </div>
      <div className="grid grid-cols-3 gap-2 font-mono text-[10px] text-zinc-500">
        <div>
          <span>Protected</span>
          <strong>₹{revenue_protected.toLocaleString()}</strong>
        </div>
        <div>
          <span>At Risk</span>
          <strong>₹{revenue_at_risk.toLocaleString()}</strong>
        </div>
        <div>
          <span>Cost</span>
          <strong>₹{cost_of_action.toLocaleString()}</strong>
        </div>
      </div>
    </div>
  );
};

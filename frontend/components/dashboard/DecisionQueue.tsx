import React, { memo } from "react";
import { Search, AlertTriangle, ShieldCheck } from "lucide-react";

export interface DecisionItem {
  id: number;
  sku: string;
  product_name: string;
  category: string;
  issue: string;
  risk_level: "Critical" | "High" | "Medium" | "Low";
  urgency: number;
  days_remaining: number;
  revenue_impact: number;
  profit_impact: number;
  confidence_score: number;
  recommended_action: string;
  reorder_quantity: number;
  owner: string;
  status: "Open" | "In Progress" | "Resolved";
}

interface DecisionQueueProps {
  decisions: DecisionItem[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  search: string;
  onSearchChange: (val: string) => void;
  category: string;
  onCategoryChange: (val: string) => void;
  riskLevel: string;
  onRiskLevelChange: (val: string) => void;
  minExposure: string;
  onMinExposureChange: (val: string) => void;
}

export const DecisionQueue: React.FC<DecisionQueueProps> = memo(
  ({
    decisions,
    selectedId,
    onSelect,
    search,
    onSearchChange,
    category,
    onCategoryChange,
    riskLevel,
    onRiskLevelChange,
    minExposure,
    onMinExposureChange,
  }) => {
    
    const riskBadgeColors = {
      Critical: "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-950/30 dark:border-rose-900/50 dark:text-rose-400",
      High: "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-950/30 dark:border-amber-900/50 dark:text-amber-400",
      Medium: "bg-zinc-50 border-zinc-200 text-zinc-700 dark:bg-zinc-900/30 dark:border-zinc-800 dark:text-zinc-400",
      Low: "bg-zinc-50 border-zinc-200 text-zinc-500 dark:bg-zinc-900/30 dark:border-zinc-800 dark:text-zinc-500",
    };

    return (
      <div 
        className="bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 p-5 rounded-xl shadow-sm flex flex-col h-[650px] space-y-4"
        role="region"
        aria-label="Inventory Decision Queue List"
      >
        <div className="space-y-1">
          <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
            System Backlog
          </span>
          <h3 className="text-lg font-bold text-zinc-900 dark:text-white tracking-tight">
            Resolutions Queue
          </h3>
        </div>

        {/* Filters Grid */}
        <div className="grid grid-cols-2 gap-2">
          {/* Search bar */}
          <div className="col-span-2 relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-400" />
            <input
              type="text"
              placeholder="Search SKU / product..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-zinc-950"
              aria-label="Search items"
            />
          </div>

          {/* Category Filter */}
          <select
            value={category}
            onChange={(e) => onCategoryChange(e.target.value)}
            className="px-2 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-zinc-950 font-mono"
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            <option value="Beverages">Beverages</option>
            <option value="Snacks">Snacks</option>
            <option value="Personal Care">Personal Care</option>
            <option value="Home Care">Home Care</option>
            <option value="Packaged Food">Packaged Food</option>
            <option value="Nutrition">Nutrition</option>
            <option value="Pharmacy">Pharmacy</option>
            <option value="Electronics">Electronics</option>
          </select>

          {/* Risk Level Filter */}
          <select
            value={riskLevel}
            onChange={(e) => onRiskLevelChange(e.target.value)}
            className="px-2 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-zinc-950 font-mono"
            aria-label="Filter by risk level"
          >
            <option value="">All Risks</option>
            <option value="Critical">Critical</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          {/* Exposure Filter */}
          <select
            value={minExposure}
            onChange={(e) => onMinExposureChange(e.target.value)}
            className="col-span-2 px-2 py-1.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-zinc-950 font-mono"
            aria-label="Filter by minimum revenue exposure"
          >
            <option value="0">All Exposure Sizes</option>
            <option value="10000">&gt; ₹10,000</option>
            <option value="50000">&gt; ₹50,000</option>
            <option value="100000">&gt; ₹1,000,000</option>
          </select>
        </div>

        {/* Scrollable list */}
        <div className="flex-1 overflow-y-auto space-y-2 pr-1" role="list">
          {decisions.length === 0 ? (
            <div className="py-10 text-center text-zinc-400 font-mono text-xs italic">
              No matching decisions in queue.
            </div>
          ) : (
            decisions.map((dec) => {
              const isSelected = selectedId === dec.id;
              return (
                <div
                  key={dec.id}
                  onClick={() => onSelect(dec.id)}
                  className={`p-4 border rounded-xl cursor-pointer transition-all duration-200 hover:shadow-sm ${
                    isSelected
                      ? "bg-zinc-950/5 border-zinc-900 dark:bg-zinc-900/40 dark:border-zinc-100"
                      : "bg-zinc-50/50 dark:bg-zinc-900/10 border-zinc-200/80 dark:border-zinc-800/80 hover:border-zinc-300 dark:hover:border-zinc-700"
                  }`}
                  role="listitem"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      onSelect(dec.id);
                    }
                  }}
                  aria-label={`${dec.sku}: ${dec.product_name}. Risk: ${dec.risk_level}. Exposure: ₹${dec.revenue_impact}`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <span className="font-mono text-xs font-bold text-zinc-500">
                      {dec.sku}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full border text-[9px] font-mono font-extrabold uppercase ${riskBadgeColors[dec.risk_level]}`}>
                      {dec.risk_level}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-zinc-900 dark:text-white leading-snug mt-1.5 truncate">
                    {dec.product_name}
                  </h4>

                  <div className="grid grid-cols-2 gap-4 mt-3 pt-2.5 border-t border-zinc-100 dark:border-zinc-800/80 font-mono text-[10px] text-zinc-500">
                    <div>
                      <span className="block uppercase text-[8px] text-zinc-400 mb-0.5">Exposure</span>
                      <strong className="text-zinc-900 dark:text-white font-bold">
                        ₹{dec.revenue_impact.toLocaleString()}
                      </strong>
                    </div>
                    <div>
                      <span className="block uppercase text-[8px] text-zinc-400 mb-0.5">Stockout</span>
                      <strong className={`font-bold ${dec.days_remaining < 7 ? "text-rose-600" : "text-zinc-900 dark:text-white"}`}>
                        {dec.days_remaining} days
                      </strong>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    );
  }
);

DecisionQueue.displayName = "DecisionQueue";

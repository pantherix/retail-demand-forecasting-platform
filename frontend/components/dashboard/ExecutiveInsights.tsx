import React, { memo, useMemo } from "react";
import { Sparkles, AlertTriangle, ShieldCheck, TrendingUp, HelpCircle } from "lucide-react";

interface ExecutiveInsightsProps {
  revenueAtRisk: number;
  criticalCount: number;
  forecastAccuracy: number;
  isUnavailable: boolean;
}

export const ExecutiveInsights: React.FC<ExecutiveInsightsProps> = memo(
  ({ revenueAtRisk, criticalCount, forecastAccuracy, isUnavailable }) => {
    
    // Dynamically calculate insights based on actual data
    const insightsList = useMemo(() => {
      if (isUnavailable) return [];

      const list = [];

      // Insight 1: Revenue at Risk / Exposure
      if (revenueAtRisk > 0) {
        list.push({
          title: "Revenue Risk Triggered",
          desc: `Total stockout exposure reaches ₹${revenueAtRisk.toLocaleString()}. Priority resolution is recommended for ${criticalCount} critical SKUs.`,
          icon: <AlertTriangle className="h-4 w-4 text-rose-600 dark:text-rose-400" />,
          bgColor: "bg-rose-50/70 border-rose-200/60 dark:bg-rose-950/20 dark:border-rose-900/40",
          textColor: "text-rose-900 dark:text-rose-300",
        });
      } else {
        list.push({
          title: "Revenue Risk Stabilized",
          desc: "Current stock covers demand expectations. No active SKU has high stockout exposure.",
          icon: <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />,
          bgColor: "bg-emerald-50/70 border-emerald-200/60 dark:bg-emerald-950/20 dark:border-emerald-900/40",
          textColor: "text-emerald-900 dark:text-emerald-300",
        });
      }

      // Insight 2: Supplier Delays
      if (criticalCount > 0) {
        list.push({
          title: "Procurement Pipeline Delay",
          desc: `Supplier transit lags are impacting ${criticalCount} SKUs. Standard lead times have degraded.`,
          icon: <TrendingUp className="h-4 w-4 text-amber-600 dark:text-amber-400" />,
          bgColor: "bg-amber-50/70 border-amber-200/60 dark:bg-amber-950/20 dark:border-amber-900/40",
          textColor: "text-amber-900 dark:text-amber-300",
        });
      }

      // Insight 3: Forecast Performance
      list.push({
        title: `Model Optimizations Complete`,
        desc: `High-confidence forecast cycles run at ${forecastAccuracy}% accuracy. Machine Learning runs have balanced replenishment recommendations.`,
        icon: <Sparkles className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />,
        bgColor: "bg-indigo-50/70 border-indigo-200/60 dark:bg-indigo-950/20 dark:border-indigo-900/40",
        textColor: "text-indigo-900 dark:text-indigo-300",
      });

      return list;
    }, [revenueAtRisk, criticalCount, forecastAccuracy, isUnavailable]);

    return (
      <div
        className="backdrop-blur-md bg-white/70 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/60 p-6 rounded-xl shadow-sm space-y-4 flex flex-col justify-between"
        role="region"
        aria-label="Executive AI Insights Panel"
      >
        <div className="space-y-1">
          <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
            Intelligence Layer
          </span>
          <h3 className="text-lg tracking-tight font-extrabold text-zinc-900 dark:text-zinc-50 flex items-center gap-1.5">
            <Sparkles className="h-4.5 w-4.5 text-zinc-600 shrink-0" />
            Executive AI Insights
          </h3>
        </div>

        {isUnavailable ? (
          <div className="py-8 text-center text-zinc-400 font-mono italic text-xs">
            Data currently unavailable
          </div>
        ) : (
          <div className="space-y-3">
            {insightsList.map((ins, idx) => (
              <div
                key={idx}
                className={`p-3.5 border rounded-lg flex items-start gap-3 transition-colors ${ins.bgColor}`}
              >
                <div className="p-1 rounded bg-[#111114] border border-zinc-200/50 dark:border-[#27272A] shadow-sm shrink-0">
                  {ins.icon}
                </div>
                <div className="space-y-1">
                  <h4 className={`text-xs font-mono font-bold uppercase tracking-wider ${ins.textColor}`}>
                    {ins.title}
                  </h4>
                  <p className="text-xs text-zinc-600 dark:text-zinc-400 leading-relaxed font-sans font-medium">
                    {ins.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
);

ExecutiveInsights.displayName = "ExecutiveInsights";

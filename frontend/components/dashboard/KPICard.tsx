import React, { memo } from "react";
import { ResponsiveContainer, AreaChart, Area } from "recharts";
import { ArrowUpRight, ArrowDownRight, AlertTriangle } from "lucide-react";
import { KPIMetric } from "../../hooks/useExecutiveMetrics";

interface KPICardProps {
  title: string;
  metric: KPIMetric;
  isCurrency?: boolean;
}

export const KPICard: React.FC<KPICardProps> = memo(({ title, metric, isCurrency = false }) => {
  const { value, trend, trendDirection, status, isUnavailable, sparklineData } = metric;

  // Set WCAG AA compliant text and sparkline colors
  const statusColors = {
    success: {
      text: "text-emerald-700 dark:text-emerald-400",
      bg: "bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800",
      sparkline: "#059669",
    },
    error: {
      text: "text-rose-700 dark:text-rose-400",
      bg: "bg-rose-50 border-rose-200 dark:bg-rose-950/30 dark:border-rose-800",
      sparkline: "#e11d48",
    },
    warning: {
      text: "text-amber-700 dark:text-amber-400",
      bg: "bg-amber-50 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800",
      sparkline: "#d97706",
    },
    neutral: {
      text: "text-zinc-600 dark:text-zinc-400",
      bg: "bg-zinc-50 border-zinc-200 dark:bg-zinc-900/30 dark:border-zinc-800",
      sparkline: "#71717a",
    },
  }[status];

  const formattedValue =
    typeof value === "number"
      ? isCurrency
        ? `₹${Number(value).toLocaleString('en-IN')}`
        : Number(value).toLocaleString('en-IN')
      : value;

  return (
    <div
      className="ferrari-panel p-5 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between h-36 relative overflow-hidden"
      role="region"
      aria-label={`${title} Metric Card`}
    >
      {/* Glossy reflection layer */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />
      <div className="flex justify-between items-start relative z-10">
        <span className="text-[11px] font-mono font-bold text-zinc-500 uppercase tracking-wider">
          {title}
        </span>
        {!isUnavailable && trend && (
          <div
            className={`flex items-center gap-0.5 px-2 py-0.5 rounded-full border text-[10px] font-mono font-extrabold ${statusColors.bg} ${statusColors.text}`}
            aria-label={`Trend direction: ${trendDirection}, Rate: ${trend}`}
          >
            {trendDirection === "up" ? (
              <ArrowUpRight className="h-3 w-3 shrink-0" />
            ) : trendDirection === "down" ? (
              <ArrowDownRight className="h-3 w-3 shrink-0" />
            ) : null}
            <span>{trend}</span>
          </div>
        )}
        {isUnavailable && (
          <div className="flex items-center gap-1 text-[10px] font-mono font-bold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
            <AlertTriangle className="h-3 w-3" />
            <span>Offline</span>
          </div>
        )}
      </div>

      <div className="mt-2 flex items-baseline justify-between gap-4 relative z-10">
        <h2 className="min-w-0 flex-1 whitespace-nowrap overflow-visible text-2xl md:text-3xl font-black tracking-tight text-white font-sans">
          {formattedValue}
        </h2>
        
        {!isUnavailable && sparklineData && sparklineData.length > 0 && (
          <div className="h-10 w-24 overflow-hidden shrink-0" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sparklineData}>
                <defs>
                  <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={statusColors.sparkline} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={statusColors.sparkline} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke={statusColors.sparkline}
                  strokeWidth={1.5}
                  fillOpacity={1}
                  fill={`url(#gradient-${title})`}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
});

KPICard.displayName = "KPICard";

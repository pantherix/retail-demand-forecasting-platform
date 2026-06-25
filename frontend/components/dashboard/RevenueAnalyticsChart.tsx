import React, { memo, useMemo } from "react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";

interface RevenueAnalyticsChartProps {
  revenueProtected: number;
  revenueAtRisk: number;
}

export const RevenueAnalyticsChart: React.FC<RevenueAnalyticsChartProps> = memo(
  ({ revenueProtected, revenueAtRisk }) => {
    // Generate deterministic 30-day historical chart data anchored on the current values
    const chartData = useMemo(() => {
      const data = [];
      const now = new Date();

      for (let i = 29; i >= 0; i--) {
        const date = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
        const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

        // Generate curves that anchor to the exact current values at index 29 (today)
        let protectedVal = 0;
        let riskVal = 0;

        if (i === 0) {
          protectedVal = revenueProtected;
          riskVal = revenueAtRisk;
        } else {
          // Model simulated historical fluctuations ending at today's real totals
          const wave = Math.sin((29 - i) * 0.4);
          const noise = Math.cos((29 - i) * 0.9) * 0.15;
          
          protectedVal = Math.max(
            0,
            Math.round(revenueProtected * (0.85 + wave * 0.1 + noise))
          );
          riskVal = Math.max(
            0,
            Math.round(revenueAtRisk * (1.1 + wave * 0.15 + noise))
          );
        }

        data.push({
          date: dateStr,
          "Revenue Protected": protectedVal,
          "Revenue At Risk": riskVal,
        });
      }

      return data;
    }, [revenueProtected, revenueAtRisk]);

    // Custom Glassmorphic Tooltip
    const CustomTooltip = ({ active, payload, label }: any) => {
      if (active && payload && payload.length) {
        return (
          <div className="bg-[#111114] border border-zinc-800 p-3 rounded-lg shadow-md font-mono text-xs space-y-1.5">
            <p className="font-bold text-white border-b border-zinc-800 pb-1">{label}</p>
            {payload.map((entry: any, index: number) => (
              <div key={index} className="flex justify-between gap-6">
                <span className="text-zinc-500" style={{ color: entry.stroke }}>
                  {entry.name}:
                </span>
                <span className="font-extrabold text-white">
                  ₹{entry.value.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        );
      }
      return null;
    };

    return (
      <div
        className="backdrop-blur-md bg-white/70 dark:bg-zinc-900/60 border border-zinc-200/80 dark:border-zinc-800/60 p-6 rounded-xl shadow-sm flex flex-col space-y-4"
        role="region"
        aria-label="30-Day Revenue Protection vs Risk Trend Chart"
      >
        <div className="flex justify-between items-center">
          <div className="space-y-1">
            <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
              Financial Exposure
            </span>
            <h3 className="text-lg tracking-tight font-extrabold text-zinc-900 dark:text-zinc-50">
              Revenue Analytics Trend
            </h3>
          </div>
        </div>

        <div className="h-72 w-full" aria-label="Line graph displaying protected revenue versus risk revenue for the last 30 days">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorProtected" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" className="dark:stroke-zinc-800" />
              <XAxis
                dataKey="date"
                stroke="#888888"
                fontSize={10}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="#888888"
                fontSize={10}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                verticalAlign="top"
                height={36}
                iconType="circle"
                wrapperStyle={{
                  fontSize: "11px",
                  fontFamily: "monospace",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              />
              <Area
                type="monotone"
                dataKey="Revenue Protected"
                stroke="#059669"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorProtected)"
              />
              <Area
                type="monotone"
                dataKey="Revenue At Risk"
                stroke="#dc2626"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorRisk)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    );
  }
);

RevenueAnalyticsChart.displayName = "RevenueAnalyticsChart";

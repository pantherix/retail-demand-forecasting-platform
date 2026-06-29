"use client";

import { useEffect, useState } from "react";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Cell, PieChart, Pie, ResponsiveContainer
} from "recharts";
import { RefreshCw, BarChart3, Zap, AlertTriangle, CheckCircle } from "lucide-react";

const MODEL_COLORS: Record<string, string> = {
  "XGBoost Ensemble": "#DC2626",
  "Random Forest Regressor": "#F59E0B",
  "Moving Average": "#6366F1",
};

const HEALTH_COLORS: Record<string, string> = {
  Good: "#22C55E",
  Fair: "#F59E0B",
  Poor: "#EF4444",
};

export default function ForecastAccuracyView() {
  const { addToast } = useToast();
  const [data, setData] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [quality, models] = await Promise.all([
        api.getForecastQuality(),
        api.getModelWins(),
      ]);
      setData(quality);
      setLeaderboard(Array.isArray(models) ? models : []);
    } catch (err: any) {
      addToast(err.message || "Failed to load forecast accuracy data.", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Build chart-ready arrays from the model_selection map
  const modelWinsData = data?.model_selection
    ? Object.entries(data.model_selection as Record<string, number>).map(([name, wins]) => ({
        name,
        wins,
      }))
    : [];

  // Build health bucket data from forecast_health map
  const healthData = data?.forecast_health
    ? Object.entries(data.forecast_health as Record<string, number>).map(([bucket, count]) => ({
        name: bucket,
        value: count,
      }))
    : [];

  // Best winning model
  const bestModel =
    modelWinsData.length > 0
      ? modelWinsData.reduce((a, b) => (a.wins >= b.wins ? a : b))
      : null;

  // Critical drifting SKU — find lowest MAPE from leaderboard (most critical = highest MAPE)
  const criticalSku =
    leaderboard.length > 0
      ? leaderboard.reduce((a: any, b: any) =>
          (a.mape ?? 0) >= (b.mape ?? 0) ? a : b
        )
      : null;

  const totalBacktests = leaderboard.length;

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <RefreshCw className="h-8 w-8 text-[#DC2626] animate-spin" />
        <p className="text-zinc-500 text-xs font-mono">LOADING TELEMETRY...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-mono font-bold text-white flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-[#DC2626]" />
            FORECAST ACCURACY TELEMETRY
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time MAPE metrics, algorithm leaderboards, and continuous backtesting wins.
          </p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-[#18181B] border border-[#27272A] hover:border-zinc-500 text-zinc-300 text-xs font-mono rounded transition-colors cursor-pointer"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          REFRESH TICKER
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-[#18181B] border border-[#27272A] p-5 rounded-lg space-y-1">
          <span className="text-[10px] font-mono text-zinc-500 uppercase">System Accuracy (Avg)</span>
          <div className="text-2xl font-bold text-white font-mono">
            {data?.forecast_accuracy != null ? `${data.forecast_accuracy.toFixed(1)}%` : "—"}
          </div>
          <div className="text-[10px] text-zinc-500 font-mono">
            MAPE: {data?.forecast_accuracy != null ? `${(100 - data.forecast_accuracy).toFixed(1)}%` : "—"}
          </div>
        </div>

        <div className="bg-[#18181B] border border-[#27272A] p-5 rounded-lg space-y-1">
          <span className="text-[10px] font-mono text-zinc-500 uppercase">Best Winning Model</span>
          <div className="text-base font-bold text-[#DC2626] font-mono leading-snug">
            {bestModel?.name ?? "—"}
          </div>
          <div className="text-[10px] text-zinc-500 font-mono">Lowest aggregate RMSE</div>
        </div>

        <div className="bg-[#18181B] border border-[#27272A] p-5 rounded-lg space-y-1">
          <span className="text-[10px] font-mono text-zinc-500 uppercase">Total Backtest Runs</span>
          <div className="text-2xl font-bold text-white font-mono">{totalBacktests.toLocaleString()}</div>
          <div className="text-[10px] text-zinc-500 font-mono">Across active SKUs</div>
        </div>

        <div className="bg-[#18181B] border border-[#27272A] p-5 rounded-lg space-y-1">
          <span className="text-[10px] font-mono text-zinc-500 uppercase">Critical Drifting SKU</span>
          <div className="text-base font-bold text-[#F59E0B] font-mono">
            {criticalSku?.sku ?? "—"}
          </div>
          <div className="text-[10px] text-zinc-500 font-mono">
            {criticalSku ? "Needs manual retune" : "All SKUs stable"}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Algorithm Wins */}
        <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[#DC2626]" />
            <h3 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">
              Telemetry Algorithm Wins (Leaderboard Distribution)
            </h3>
          </div>

          {modelWinsData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
              No algorithm telemetry available.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={modelWinsData} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272A" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#71717A", fontSize: 10, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#71717A", fontSize: 10, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#18181B",
                    border: "1px solid #27272A",
                    borderRadius: 6,
                    color: "#fff",
                    fontSize: 11,
                    fontFamily: "monospace",
                  }}
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                />
                <Bar dataKey="wins" radius={[3, 3, 0, 0]}>
                  {modelWinsData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={MODEL_COLORS[entry.name] ?? "#6B7280"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Forecast Health Buckets */}
        <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-[#F59E0B]" />
            <h3 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">
              Forecast Health &amp; MAPE Buckets
            </h3>
          </div>

          {healthData.every((d) => d.value === 0) ? (
            <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
              No accuracy bucket telemetry available.
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={healthData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    dataKey="value"
                    paddingAngle={3}
                    label={({ name, percent }) =>
                      `${name} ${((percent ?? 0) * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {healthData.map((entry, idx) => (
                      <Cell
                        key={idx}
                        fill={HEALTH_COLORS[entry.name] ?? "#6B7280"}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#18181B",
                      border: "1px solid #27272A",
                      borderRadius: 6,
                      color: "#fff",
                      fontSize: 11,
                      fontFamily: "monospace",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>

              {/* Legend */}
              <div className="flex justify-center gap-4 flex-wrap">
                {healthData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-400">
                    <span
                      className="w-2.5 h-2.5 rounded-full inline-block"
                      style={{ background: HEALTH_COLORS[entry.name] ?? "#6B7280" }}
                    />
                    {entry.name}: {entry.value}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Model Leaderboard Table */}
      <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
        <div className="flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-zinc-400" />
          <h3 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">
            Model Leaderboard — Sorted by RMSE
          </h3>
        </div>

        {leaderboard.length === 0 ? (
          <div className="flex items-center justify-center py-10 text-zinc-500 text-xs font-mono">
            No training runs recorded yet. Upload a dataset and retrain to populate the leaderboard.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono text-zinc-300">
              <thead>
                <tr className="border-b border-[#27272A] text-[10px] text-zinc-500 uppercase">
                  <th className="text-left py-2 px-3">Rank</th>
                  <th className="text-left py-2 px-3">SKU</th>
                  <th className="text-left py-2 px-3">Model</th>
                  <th className="text-right py-2 px-3">RMSE</th>
                  <th className="text-right py-2 px-3">MAE</th>
                  <th className="text-right py-2 px-3">MAPE %</th>
                  <th className="text-right py-2 px-3">Samples</th>
                  <th className="text-left py-2 px-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.slice(0, 20).map((run: any, idx: number) => {
                  const mape = run.mape ?? 0;
                  const status = mape < 15 ? "Good" : mape < 30 ? "Fair" : "Poor";
                  const StatusIcon =
                    status === "Good"
                      ? CheckCircle
                      : status === "Fair"
                      ? AlertTriangle
                      : AlertTriangle;
                  return (
                    <tr
                      key={idx}
                      className="border-b border-[#27272A]/40 hover:bg-[#27272A]/20 transition-colors"
                    >
                      <td className="py-2 px-3 text-zinc-500">#{run.rank ?? idx + 1}</td>
                      <td className="py-2 px-3 text-white font-bold">{run.sku}</td>
                      <td className="py-2 px-3">
                        <span
                          className="px-2 py-0.5 rounded text-[9px] font-bold"
                          style={{
                            background: (MODEL_COLORS[run.model] ?? "#6B7280") + "22",
                            color: MODEL_COLORS[run.model] ?? "#6B7280",
                            border: `1px solid ${(MODEL_COLORS[run.model] ?? "#6B7280")}44`,
                          }}
                        >
                          {run.model}
                        </span>
                      </td>
                      <td className="py-2 px-3 text-right">{run.rmse?.toFixed(2) ?? "—"}</td>
                      <td className="py-2 px-3 text-right">{run.mae?.toFixed(2) ?? "—"}</td>
                      <td className="py-2 px-3 text-right">{run.mape?.toFixed(1) ?? "—"}%</td>
                      <td className="py-2 px-3 text-right text-zinc-400">{run.samples?.toLocaleString() ?? "—"}</td>
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-1">
                          <StatusIcon
                            className="h-3.5 w-3.5"
                            style={{ color: HEALTH_COLORS[status] }}
                          />
                          <span style={{ color: HEALTH_COLORS[status] }}>{status}</span>
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
    </div>
  );
}

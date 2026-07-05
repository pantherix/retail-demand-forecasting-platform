"use client";

import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Cell, PieChart, Pie, ResponsiveContainer
} from "recharts";
import { RefreshCw, BarChart3, Zap, AlertTriangle, CheckCircle, Trophy, Gauge, Activity } from "lucide-react";

const MODEL_COLORS: Record<string, string> = {
  "XGBoost Ensemble": "#FF1B1B",
  "Random Forest Regressor": "#F59E0B",
  "Moving Average": "#6366F1",
};

const MODEL_GRADIENTS: Record<string, string> = {
  "XGBoost Ensemble": "url(#glowRed)",
  "Random Forest Regressor": "url(#glowAmber)",
  "Moving Average": "url(#glowIndigo)",
};

const HEALTH_COLORS: Record<string, string> = {
  Good: "#10B981",
  Fair: "#F59E0B",
  Poor: "#EF4444",
};

const HEALTH_GRADIENTS: Record<string, string> = {
  Good: "url(#glowGreen)",
  Fair: "url(#glowAmberPie)",
  Poor: "url(#glowRedPie)",
};

export default function ForecastAccuracyView() {
  const { addToast } = useToast();
  const { selectedDatasetId, refreshTrigger } = useStore();
  const [data, setData] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [quality, models] = await Promise.all([
        api.getForecastQuality(selectedDatasetId || undefined),
        api.getModelWins(selectedDatasetId || undefined),
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
  }, [selectedDatasetId, refreshTrigger]);

  // Build chart-ready arrays from the model_selection map
  const modelWinsData = useMemo(() => {
    return data?.model_selection
      ? Object.entries(data.model_selection as Record<string, number>).map(([name, wins]) => ({
          name,
          wins,
        }))
      : [];
  }, [data]);

  // Build health bucket data from forecast_health map
  const healthData = useMemo(() => {
    return data?.forecast_health
      ? Object.entries(data.forecast_health as Record<string, number>).map(([bucket, count]) => ({
          name: bucket,
          value: count,
        }))
      : [];
  }, [data]);

  // Best winning model
  const bestModel = useMemo(() => {
    return modelWinsData.length > 0
      ? modelWinsData.reduce((a, b) => (a.wins >= b.wins ? a : b))
      : null;
  }, [modelWinsData]);

  // Critical drifting SKU ─ find lowest MAPE from leaderboard
  const criticalSku = useMemo(() => {
    return leaderboard.length > 0
      ? leaderboard.reduce((a: any, b: any) =>
          (a.mape ?? 0) >= (b.mape ?? 0) ? a : b
        )
      : null;
  }, [leaderboard]);

  const totalBacktests = useMemo(() => leaderboard.length, [leaderboard]);

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse py-2">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-black/40 border border-zinc-800/80 p-5 rounded-lg h-24 flex flex-col justify-between">
              <div className="h-3 bg-zinc-800 rounded w-2/3" />
              <div className="h-6 bg-zinc-800 rounded w-1/2" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-black/40 border border-zinc-800 p-6 rounded-lg h-80 flex flex-col justify-between">
            <div className="h-4 bg-zinc-800 rounded w-1/3" />
            <div className="h-48 bg-zinc-800/60 rounded w-full" />
          </div>
          <div className="bg-black/40 border border-zinc-800 p-6 rounded-lg h-80 flex flex-col justify-between">
            <div className="h-4 bg-zinc-800 rounded w-1/3" />
            <div className="h-48 bg-zinc-800/60 rounded w-full" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ferrari-panel p-8 space-y-8 text-zinc-100 font-sans shadow-2xl relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-[#E10600]/5 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[#E10600]/5 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/10 pb-6 relative z-10">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-white flex items-center gap-2">
            <Activity className="h-5 w-5 text-red-600" /> FORECAST ACCURACY TELEMETRY
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time MAPE metrics, algorithm wins distribution, and continuous ML backtesting leaderboard.
          </p>
        </div>
        <div>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-1.5 border border-white/10 bg-white/5 hover:bg-white/10 text-zinc-300 rounded text-xs transition-all font-mono cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" /> REFRESH TICKER
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 relative z-10">
        {/* Card 1: System Accuracy */}
        <div className="bg-black/30 border border-red-500/10 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group hover:border-red-500/30 transition-all duration-300">
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">System Accuracy (Avg)</span>
            <h3 className="text-2xl font-bold font-mono text-red-500">
              {data?.forecast_accuracy != null ? `${data.forecast_accuracy.toFixed(1)}%` : "—"}
            </h3>
            <p className="text-[10px] text-zinc-500 font-mono">
              MAPE: {data?.forecast_accuracy != null ? `${(100 - data.forecast_accuracy).toFixed(1)}%` : "—"}
            </p>
          </div>
          <div className="h-10 w-10 bg-red-950/20 border border-red-500/20 rounded flex items-center justify-center text-red-400">
            <Gauge className="h-5 w-5" />
          </div>
        </div>

        {/* Card 2: Best Winning Model */}
        <div className="bg-black/30 border border-amber-500/10 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group hover:border-amber-500/30 transition-all duration-300">
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Best Winning Model</span>
            <h3 className="text-sm font-bold font-mono text-amber-500 truncate max-w-[150px] leading-tight">
              {bestModel?.name ?? "—"}
            </h3>
            <p className="text-[10px] text-zinc-500 font-mono">Lowest aggregate RMSE</p>
          </div>
          <div className="h-10 w-10 bg-amber-950/20 border border-amber-500/20 rounded flex items-center justify-center text-amber-400">
            <Trophy className="h-5 w-5" />
          </div>
        </div>

        {/* Card 3: Total Backtest Runs */}
        <div className="bg-black/30 border border-white/5 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group hover:border-white/10 transition-all duration-300">
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Total Backtest Runs</span>
            <h3 className="text-2xl font-bold font-mono text-white">
              {totalBacktests.toLocaleString()}
            </h3>
            <p className="text-[10px] text-zinc-500 font-mono">Across active SKUs</p>
          </div>
          <div className="h-10 w-10 bg-zinc-900 border border-white/5 rounded flex items-center justify-center text-zinc-400">
            <BarChart3 className="h-5 w-5" />
          </div>
        </div>

        {/* Card 4: Critical Drifting SKU */}
        <div className="bg-black/30 border border-yellow-500/10 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group hover:border-yellow-500/30 transition-all duration-300">
          <div className="space-y-1">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Critical Drifting SKU</span>
            <h3 className="text-sm font-bold font-mono text-yellow-500">
              {criticalSku?.sku ?? "—"}
            </h3>
            <p className="text-[10px] text-zinc-500 font-mono">
              {criticalSku ? "Needs manual retune" : "All SKUs stable"}
            </p>
          </div>
          <div className="h-10 w-10 bg-yellow-950/20 border border-yellow-500/20 rounded flex items-center justify-center text-yellow-400">
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        {/* Algorithm Wins */}
        <div className="bg-black/30 border border-white/5 p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-2 border-b border-white/5 pb-3">
            <BarChart3 className="h-4 w-4 text-red-600" />
            <h3 className="text-xs font-mono font-bold text-zinc-300 uppercase tracking-wider">
              Telemetry Algorithm Wins (Leaderboard Distribution)
            </h3>
          </div>

          {modelWinsData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
              No algorithm telemetry available.
            </div>
          ) : (
            <div className="relative h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
              <BarChart data={modelWinsData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                <defs>
                  <linearGradient id="glowRed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#FF1B1B" stopOpacity={0.85} />
                    <stop offset="100%" stopColor="#7a0000" stopOpacity={0.15} />
                  </linearGradient>
                  <linearGradient id="glowAmber" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.85} />
                    <stop offset="100%" stopColor="#78350F" stopOpacity={0.15} />
                  </linearGradient>
                  <linearGradient id="glowIndigo" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366F1" stopOpacity={0.85} />
                    <stop offset="100%" stopColor="#312E81" stopOpacity={0.15} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#A1A1AA", fontSize: 9, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#A1A1AA", fontSize: 9, fontFamily: "monospace" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "rgba(9, 9, 11, 0.9)",
                    border: "1px solid rgba(255, 27, 27, 0.25)",
                    borderRadius: 6,
                    color: "#fff",
                    fontSize: 10,
                    fontFamily: "monospace",
                  }}
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                />
                <Bar dataKey="wins" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                  {modelWinsData.map((entry, idx) => (
                    <Cell
                      key={idx}
                      fill={MODEL_COLORS[entry.name] ?? "#6B7280"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          )}
        </div>

        {/* Forecast Health Buckets */}
        <div className="bg-black/30 border border-white/5 p-6 rounded-lg space-y-4">
          <div className="flex items-center gap-2 border-b border-white/5 pb-3">
            <Zap className="h-4 w-4 text-amber-500" />
            <h3 className="text-xs font-mono font-bold text-zinc-300 uppercase tracking-wider">
              Forecast Health &amp; MAPE Buckets
            </h3>
          </div>

          {healthData.every((d) => d.value === 0) ? (
            <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
              No accuracy bucket telemetry available.
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="relative h-[180px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <defs>
                    <linearGradient id="glowGreen" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity={0.85} />
                      <stop offset="100%" stopColor="#064E3B" stopOpacity={0.2} />
                    </linearGradient>
                    <linearGradient id="glowAmberPie" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#F59E0B" stopOpacity={0.85} />
                      <stop offset="100%" stopColor="#78350F" stopOpacity={0.2} />
                    </linearGradient>
                    <linearGradient id="glowRedPie" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#EF4444" stopOpacity={0.85} />
                      <stop offset="100%" stopColor="#7f1d1d" stopOpacity={0.2} />
                    </linearGradient>
                  </defs>
                  <Pie
                    data={healthData}
                    cx="50%"
                    cy="50%"
                    isAnimationActive={false}
                    innerRadius={45}
                    outerRadius={70}
                    dataKey="value"
                    paddingAngle={4}
                    label={({ percent }) =>
                      `${((percent ?? 0) * 100).toFixed(0)}%`
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
                      background: "rgba(9, 9, 11, 0.9)",
                      border: "1px solid rgba(255, 27, 27, 0.25)",
                      borderRadius: 6,
                      color: "#fff",
                      fontSize: 10,
                      fontFamily: "monospace",
                    }}
                  />
                </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Legend */}
              <div className="flex justify-center gap-4 flex-wrap">
                {healthData.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-400">
                    <span
                      className="w-2.5 h-2.5 rounded-full inline-block border border-white/10"
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
      <div className="bg-black/30 border border-white/5 p-6 rounded-lg space-y-4 relative z-10">
        <div className="flex items-center gap-2 border-b border-white/5 pb-3">
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
            <table className="w-full text-xs font-mono text-zinc-300 border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-[9px] text-zinc-500 uppercase tracking-wider">
                  <th className="text-left py-3 px-4 font-black">Rank</th>
                  <th className="text-left py-3 px-4 font-black">SKU</th>
                  <th className="text-left py-3 px-4 font-black">Model</th>
                  <th className="text-right py-3 px-4 font-black">RMSE</th>
                  <th className="text-right py-3 px-4 font-black">MAE</th>
                  <th className="text-right py-3 px-4 font-black">MAPE %</th>
                  <th className="text-right py-3 px-4 font-black">Samples</th>
                  <th className="text-left py-3 px-4 font-black">Status</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.slice(0, 25).map((run: any, idx: number) => {
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
                      className="border-b border-white/5 hover:bg-white/5 transition-all duration-200"
                    >
                      <td className="py-2.5 px-4 text-zinc-550 font-bold">#{run.rank ?? idx + 1}</td>
                      <td className="py-2.5 px-4 text-white font-bold">{run.sku}</td>
                      <td className="py-2.5 px-4">
                        <span
                          className="px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-wider"
                          style={{
                            background: (MODEL_COLORS[run.model] ?? "#6B7280") + "18",
                            color: MODEL_COLORS[run.model] ?? "#6B7280",
                            border: `1px solid ${(MODEL_COLORS[run.model] ?? "#6B7280")}33`,
                          }}
                        >
                          {run.model}
                        </span>
                      </td>
                      <td className="py-2.5 px-4 text-right font-bold text-zinc-100">{run.rmse?.toFixed(2) ?? "—"}</td>
                      <td className="py-2.5 px-4 text-right text-zinc-350">{run.mae?.toFixed(2) ?? "—"}</td>
                      <td className="py-2.5 px-4 text-right text-zinc-100 font-bold">{run.mape?.toFixed(1) ?? "—"}%</td>
                      <td className="py-2.5 px-4 text-right text-zinc-500 font-black">{run.samples?.toLocaleString() ?? "—"}</td>
                      <td className="py-2.5 px-4">
                        <div className="flex items-center gap-1.5 font-bold">
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

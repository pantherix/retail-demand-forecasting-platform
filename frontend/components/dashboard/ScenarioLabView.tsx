"use client";

import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard, ScenarioPanel } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { ErrorState } from "../ui/ErrorState";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

export default function ScenarioLabView() {
  const refreshTrigger = useStore((state) => state.refreshTrigger);
  const triggerRefresh = useStore((state) => state.triggerRefresh);
  const { addToast } = useToast();

  const [demandChange, setDemandChange] = useState<number>(0);
  const [leadTimeChange, setLeadTimeChange] = useState<number>(0);
  const [reliabilityChange, setReliabilityChange] = useState<number>(0);
  const [safetyStockMultiplier, setSafetyStockMultiplier] = useState<number>(1.0);
  const [leadTimeBuffer, setLeadTimeBuffer] = useState<number>(0);
  
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [executingTransfer, setExecutingTransfer] = useState<Record<string, boolean>>({});

  const runSimulation = async (
    dChange = demandChange,
    lChange = leadTimeChange,
    rChange = reliabilityChange,
    sMult = safetyStockMultiplier,
    lBuf = leadTimeBuffer
  ) => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.runScenario({
        demand_change_pct: dChange,
        lead_time_change_days: lChange,
        supplier_reliability_change_pct: rChange,
        safety_stock_multiplier: sMult,
        lead_time_buffer_days: lBuf,
      });
      // Defensively structure the data object to protect frontend mapping operations
      setData({
        skus: Array.isArray(res?.skus) ? res.skus : [],
        suggested_transfers: Array.isArray(res?.suggested_transfers) ? res.suggested_transfers : [],
        summary: res?.summary || null
      });
      setLoading(false);
    } catch (err: any) {
      setErrorMsg(err.message || "Simulation matrix failed to compute.");
      setLoading(false);
    }
  };

  // Trigger base configuration on load
  useEffect(() => {
    runSimulation(0, 0, 0, 1.0, 0);
  }, [refreshTrigger]);

  const handleReset = () => {
    setDemandChange(0);
    setLeadTimeChange(0);
    setReliabilityChange(0);
    setSafetyStockMultiplier(1.0);
    setLeadTimeBuffer(0);
    runSimulation(0, 0, 0, 1.0, 0);
  };

  // Optimistic UI Transfer Pipeline
  const handleExecuteTransfer = async (transfer: any) => {
    if (!transfer?.sku) return;
    const key = `${transfer.sku}-transfer`;
    if (executingTransfer[key]) return;
    
    setExecutingTransfer(prev => ({ ...prev, [key]: true }));
    const originalData = data ? { ...data } : null;

    // Filter items out using properties unique to the SKU, avoiding index-shifting bugs
    if (data?.suggested_transfers) {
      setData((prev: any) => ({
        ...prev,
        suggested_transfers: prev.suggested_transfers.filter((t: any) => t.sku !== transfer.sku)
      }));
    }

    try {
      await api.createTransfer({
        from_wh: transfer.from_warehouse,
        to_wh: transfer.to_warehouse,
        sku: transfer.sku,
        quantity: transfer.quantity,
      });
      addToast(`Stock transfer authorized under stress parameters. Shipped ${transfer.quantity.toLocaleString()} units.`, "success");
      runSimulation();
      triggerRefresh();
    } catch (err: any) {
      // Revert local state to match backend records if the request fails
      if (originalData) setData(originalData);
      addToast(err.message || "Fulfillment transfer routing failed", "error");
    } finally {
      setExecutingTransfer(prev => ({ ...prev, [key]: false }));
    }
  };

  // Safely extract the highest priority simulation transfer recommendation
  const simulatedTransfer = useMemo(() => {
    if (!data?.suggested_transfers || data.suggested_transfers.length === 0) return null;
    return [...data.suggested_transfers].sort((a: any, b: any) => {
      const impactA = a.financial_impact || a.revenue_impact || 0;
      const impactB = b.financial_impact || b.revenue_impact || 0;
      return impactB - impactA;
    })[0];
  }, [data]);

  if (loading && !data) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 py-2">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  if (errorMsg) {
    return <ErrorState message={errorMsg} onRetry={() => runSimulation()} />;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 relative py-2">
      <ScenarioPanel
        demandChange={demandChange}
        leadTimeChange={leadTimeChange}
        reliabilityChange={reliabilityChange}
        safetyStockMultiplier={safetyStockMultiplier}
        leadTimeBuffer={leadTimeBuffer}
        loading={loading}
        onDemandChange={setDemandChange}
        onLeadTimeChange={setLeadTimeChange}
        onReliabilityChange={setReliabilityChange}
        onSafetyStockMultiplierChange={setSafetyStockMultiplier}
        onLeadTimeBufferChange={setLeadTimeBuffer}
        onSimulate={() => runSimulation()}
        onReset={handleReset}
      />

      {loading && data && (
        <div className="space-y-4">
          <CardSkeleton />
        </div>
      )}

      {!loading && data && (
        <>
          {/* Side-by-Side Comparison Chart */}
          <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg shadow-sm space-y-4">
            <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">
              Simulation Comparison Analytics
            </span>
            <h3 className="text-lg font-mono font-bold text-zinc-900 dark:text-zinc-50">
              Financial Impact: Baseline vs. Simulated
            </h3>
            
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    {
                      name: "Revenue at Risk",
                      Baseline: data.summary?.baseline?.revenue_at_risk || 0,
                      Simulated: data.summary?.simulated?.revenue_at_risk || 0,
                    },
                    {
                      name: "Profit at Risk",
                      Baseline: data.summary?.baseline?.profit_at_risk || 0,
                      Simulated: data.summary?.simulated?.profit_at_risk || 0,
                    }
                  ]}
                  margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" className="dark:stroke-zinc-800" />
                  <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis
                    stroke="#888888"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    content={({ active, payload, label }: any) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-[#111114] border border-zinc-800 p-3 rounded-lg shadow-md font-mono text-xs space-y-1">
                            <p className="font-bold text-white border-b border-zinc-800 pb-1">{label}</p>
                            {payload.map((entry: any, idx: number) => (
                              <div key={idx} className="flex justify-between gap-6">
                                <span style={{ color: entry.fill }}>{entry.name}:</span>
                                <span className="font-bold text-white">₹{entry.value.toLocaleString()}</span>
                              </div>
                            ))}
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace" }} />
                  <Bar dataKey="Baseline" fill="#71717a" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Simulated" fill="#dc2626" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Spotlight Section for Top Simulation Recommendations */}
          {simulatedTransfer && (
            <div className="space-y-4">
              <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
                Critical Simulated Mitigation
              </span>
              <HeroActionCard
                title={`Fulfill Deficit for SKU ${simulatedTransfer.sku}`}
                description={`Environmental shock risks ₹${(simulatedTransfer.financial_impact || 0).toLocaleString()} for ${simulatedTransfer.product_name || "Target Item"}. Move ${(simulatedTransfer.quantity || 0).toLocaleString()} units from ${simulatedTransfer.from_warehouse || "Source Whse"} to balance inventory levels.`}
                actionLabel="STRESS TEST MITIGATION"
                buttonText={executingTransfer[`${simulatedTransfer.sku}-transfer`] ? "Authorizing..." : "Authorize Transfer"}
                colorClass="border-red-500"
                disabled={executingTransfer[`${simulatedTransfer.sku}-transfer`]}
                onExecute={() => handleExecuteTransfer(simulatedTransfer)}
              />
            </div>
          )}

          {/* Simulation Output Ledger Grid */}
          <div className="space-y-4">
            <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
              Simulated SKU Backlog
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(data.skus || []).map((sku: any) => {
                if (!sku?.baseline || !sku?.simulated) return null;
                const demandIncreased = sku.simulated.forecast_30d > sku.baseline.forecast_30d;
                const riskIncreased = (sku.simulated.revenue_at_risk || 0) > (sku.baseline.revenue_at_risk || 0);
                
                return (
                  <div key={sku.sku} className="bg-[#111114] border border-zinc-800 p-6 rounded-lg space-y-3 shadow-sm">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-xs font-bold text-zinc-400">{sku.sku}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono border ${
                        sku.simulated.status === "Healthy" 
                          ? "bg-green-50 dark:bg-green-950/20 text-green-600 border-green-200" 
                          : "bg-red-50 dark:bg-red-950/20 text-red-600 border-red-200"
                      }`}>
                        {sku.simulated.status || "Unknown"}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-50 leading-snug">{sku.name}</h3>
                      <p className="text-xs text-zinc-500 mt-1">Current Stock: {(sku.current_stock || 0).toLocaleString()} units</p>
                    </div>
                    <div className="pt-2 border-t border-zinc-800 grid grid-cols-2 gap-3 font-mono text-[10px] text-zinc-500">
                      <div>
                        <span className="block uppercase text-[8px] text-zinc-400">30d Demand Shift</span>
                        <span className={demandIncreased ? "text-red-500 font-bold" : "text-zinc-200"}>
                          {(sku.baseline.forecast_30d || 0).toLocaleString()} ➔ {(sku.simulated.forecast_30d || 0).toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="block uppercase text-[8px] text-zinc-400">Risk Delta</span>
                        <span className={riskIncreased ? "text-red-500 font-bold" : "text-zinc-200"}>
                          ₹{(sku.baseline.revenue_at_risk || 0).toLocaleString()} ➔ ₹{(sku.simulated.revenue_at_risk || 0).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
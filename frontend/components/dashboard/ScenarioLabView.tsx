import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard, ScenarioPanel } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { ErrorState } from "../ui/ErrorState";

export default function ScenarioLabView() {
  const { refreshTrigger, triggerRefresh } = useStore();
  const { addToast } = useToast();

  const [demandChange, setDemandChange] = useState<number>(0);
  const [leadTimeChange, setLeadTimeChange] = useState<number>(0);
  const [reliabilityChange, setReliabilityChange] = useState<number>(0);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [executingTransfer, setExecutingTransfer] = useState<Record<string, boolean>>({});

  const runSimulation = (dChange = demandChange, lChange = leadTimeChange, rChange = reliabilityChange) => {
    setLoading(true);
    setErrorMsg(null);
    api.runScenario({
      demand_change_pct: dChange,
      lead_time_change_days: lChange,
      supplier_reliability_change_pct: rChange,
    })
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Simulation failed to compute.");
        setLoading(false);
      });
  };

  useEffect(() => {
    runSimulation(0, 0, 0);
  }, [refreshTrigger]);

  const handleReset = () => {
    setDemandChange(0);
    setLeadTimeChange(0);
    setReliabilityChange(0);
    runSimulation(0, 0, 0);
  };

  // OPTIMISTIC ACTIONS: handleExecuteTransfer (transfer execution)
  const handleExecuteTransfer = async (transfer: any, index: number) => {
    const key = `${transfer.sku}-${index}`;
    if (executingTransfer[key]) return;
    
    setExecutingTransfer(prev => ({ ...prev, [key]: true }));

    const originalData = data ? { ...data } : null;

    // Optimistically filter out from suggested simulated transfers
    if (data && data.suggested_transfers) {
      setData((prev: any) => ({
        ...prev,
        suggested_transfers: prev.suggested_transfers.filter((t: any, idx: number) => idx !== index)
      }));
    }

    try {
      await api.createTransfer({
        from_wh: transfer.from_warehouse,
        to_wh: transfer.to_warehouse,
        sku: transfer.sku,
        quantity: transfer.quantity,
      });
      addToast(`Stock transfer authorized under stress parameters. Shipped ${transfer.quantity} units.`, "success");
      runSimulation();
      triggerRefresh();
    } catch (err: any) {
      // Rollback
      if (originalData) setData(originalData);
      addToast(err.message || "Fulfillment transfer failed", "error");
    } finally {
      setExecutingTransfer(prev => ({ ...prev, [key]: false }));
    }
  };

  // Memoize simulated transfer sorted by impact
  const simulatedTransfer = useMemo(() => {
    if (!data || !data.suggested_transfers) return null;
    return [...data.suggested_transfers].sort((a: any, b: any) => b.financial_impact - a.financial_impact)[0];
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
      {/* ScenarioPanel */}
      <ScenarioPanel
        demandChange={demandChange}
        leadTimeChange={leadTimeChange}
        reliabilityChange={reliabilityChange}
        loading={loading}
        onDemandChange={setDemandChange}
        onLeadTimeChange={setLeadTimeChange}
        onReliabilityChange={setReliabilityChange}
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
          {/* SPOTLIGHT SIMULATED ACTION */}
          {simulatedTransfer && (
            <div className="space-y-4">
              <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-widest block">Critical Simulated Mitigation</span>
              <HeroActionCard
                title={`Fulfill Deficit for SKU ${simulatedTransfer.sku}`}
                description={`Environmental shock risks ₹${simulatedTransfer.financial_impact.toLocaleString()} for ${simulatedTransfer.product_name}. Move ${simulatedTransfer.quantity.toLocaleString()} units from ${simulatedTransfer.from_warehouse} to balance warehouse.`}
                actionLabel="STRESS TEST MITIGATION"
                buttonText={executingTransfer[`${simulatedTransfer.sku}-99`] ? "Authorizing..." : "Authorize Transfer"}
                colorClass="border-red-500"
                disabled={executingTransfer[`${simulatedTransfer.sku}-99`]}
                onExecute={() => handleExecuteTransfer(simulatedTransfer, 99)}
              />
            </div>
          )}

          {/* SIMULATED LEDGER AS CARDS */}
          <div className="space-y-4">
            <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-555 uppercase tracking-widest block">Simulated SKU Backlog</span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data.skus.map((sku: any) => {
                const demandIncreased = sku.simulated.forecast_30d > sku.baseline.forecast_30d;
                const riskIncreased = sku.simulated.revenue_at_risk > sku.baseline.revenue_at_risk;
                return (
                  <div key={sku.sku} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 rounded-lg space-y-3 shadow-sm">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-xs font-bold text-zinc-405 dark:text-zinc-500">{sku.sku}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono border ${
                        sku.simulated.status === "Healthy" ? "bg-green-50 dark:bg-green-955/20 text-green-600 dark:text-green-400 border-green-200 dark:border-green-905/40" : "bg-red-50 dark:bg-red-955/20 text-red-600 dark:text-red-400 border-red-200 dark:border-red-905/40"
                      }`}>
                        {sku.simulated.status}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-zinc-955 dark:text-zinc-50 leading-snug">{sku.name}</h3>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">Current Stock: {sku.current_stock.toLocaleString()} units</p>
                    </div>
                    <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 grid grid-cols-2 gap-3 font-mono text-[10px] text-zinc-500">
                      <div>
                        <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">30d Demand Shift</span>
                        <span className={demandIncreased ? "text-red-650 dark:text-red-400 font-bold" : "text-zinc-900 dark:text-zinc-250 font-medium"}>
                          {sku.baseline.forecast_30d.toLocaleString()} ➔ {sku.simulated.forecast_30d.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">Risk Delta</span>
                        <span className={riskIncreased ? "text-red-650 dark:text-red-400 font-bold" : "text-zinc-900 dark:text-zinc-250 font-medium"}>
                          ₹{sku.baseline.revenue_at_risk.toLocaleString()} ➔ ₹{sku.simulated.revenue_at_risk.toLocaleString()}
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

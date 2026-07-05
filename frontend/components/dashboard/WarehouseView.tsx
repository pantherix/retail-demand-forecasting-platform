import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";
import { ShieldAlert } from "lucide-react";

export default function WarehouseView() {
  const { refreshTrigger, triggerRefresh, setActiveSku, setActiveTab, selectedDatasetId } = useStore();
  const { addToast } = useToast();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Submitting tracker for specific transfers
  const [submittingTransferSku, setSubmittingTransferSku] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getWarehouses(selectedDatasetId || undefined)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load warehouses network data.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger, selectedDatasetId]);

  // OPTIMISTIC ACTIONS: handleTransfer (transfer execution)
  const handleTransfer = async (transfer: any) => {
    if (submittingTransferSku) return;
    const transferKey = `${transfer.sku}-${transfer.from_warehouse}-${transfer.to_warehouse}`;
    setSubmittingTransferSku(transferKey);

    const originalData = data ? { ...data } : null;

    // Optimistically filter out from suggested transfers list
    if (data && data.suggested_transfers) {
      setData((prev: any) => ({
        ...prev,
        suggested_transfers: prev.suggested_transfers.filter(
          (t: any) => !(t.sku === transfer.sku && t.from_warehouse === transfer.from_warehouse && t.to_warehouse === transfer.to_warehouse)
        )
      }));
    }

    try {
      await api.createTransfer({
        from_wh: transfer.from_warehouse,
        to_wh: transfer.to_warehouse,
        sku: transfer.sku,
        quantity: transfer.quantity
      });
      addToast(`Warehouse stock transfer executed. Shipped ${transfer.quantity} units of ${transfer.sku}.`, "success");
      triggerRefresh();
    } catch (err: any) {
      // Rollback on failure
      if (originalData) setData(originalData);
      addToast(err.message || "Transfer failed", "error");
    } finally {
      setSubmittingTransferSku(null);
    }
  };

  // Memoize suggested transfers sorted by financial impact
  const sortedTransfers = useMemo(() => {
    if (!data || !data.suggested_transfers) return [];
    return [...data.suggested_transfers].sort((a: any, b: any) => b.financial_impact - a.financial_impact);
  }, [data]);

  // Memoize top transfer
  const topTransfer = useMemo(() => {
    return sortedTransfers[0];
  }, [sortedTransfers]);

  const { netCapacity, netUnits, netUtilization, netValue, netSkuClasses, netWarehouses } = useMemo(() => {
    if (!data || !data.warehouses) {
      return { netCapacity: 0, netUnits: 0, netUtilization: "0.0", netValue: 0, netSkuClasses: 0, netWarehouses: 0 };
    }
    const cap = data.warehouses.reduce((sum: number, wh: any) => sum + (wh.capacity || 0), 0);
    const units = data.warehouses.reduce((sum: number, wh: any) => sum + (wh.total_units || 0), 0);
    const val = data.warehouses.reduce((sum: number, wh: any) => sum + (wh.inventory_value || 0), 0);
    const skus = data.warehouses.reduce((sum: number, wh: any) => sum + (wh.total_items || 0), 0);
    const util = cap > 0 ? ((units / cap) * 100).toFixed(1) : "0.0";
    return {
      netCapacity: cap,
      netUnits: units,
      netUtilization: util,
      netValue: Math.round(val),
      netSkuClasses: skus,
      netWarehouses: data.warehouses.length
    };
  }, [data]);

  if (loading && !data) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 py-2">
        <CardSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  if (errorMsg) {
    return <ErrorState message={errorMsg} onRetry={fetchData} />;
  }

  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-2">
      {topTransfer && (
        <div className="space-y-4">
          <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Critical Inter-Warehouse Transfer</span>
          <HeroActionCard
            title={`Move ${topTransfer.quantity.toLocaleString()} units of ${topTransfer.sku}`}
            description={`Transfer excess inventory from surplus warehouse ${topTransfer.from_warehouse} to balance localized stockout at ${topTransfer.to_warehouse}. Captures ₹${topTransfer.financial_impact.toLocaleString()} in demand.`}
            actionLabel="BALANCING TRANSFER"
            buttonText={submittingTransferSku === `${topTransfer.sku}-${topTransfer.from_warehouse}-${topTransfer.to_warehouse}` ? "Executing..." : "Execute Transfer"}
            colorClass="border-green-500"
            disabled={!!submittingTransferSku}
            onExecute={() => handleTransfer(topTransfer)}
            onSkuClick={() => { setActiveSku(topTransfer.sku); setActiveTab("product-intelligence"); }}
          />
        </div>
      )}

      {/* NODE GRID */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {data.warehouses.map((wh: any) => (
          <div key={wh.id} className="bg-surface border border-muted p-5 rounded-lg space-y-3 shadow-sm transition-standard hover:scale-105">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold text-zinc-955 dark:text-zinc-50 text-sm">{wh.name}</h3>
                <span className="text-[10px] font-mono text-zinc-400 dark:text-zinc-550 uppercase">{wh.location}</span>
              </div>
              <span className="text-xs font-mono font-bold text-zinc-800 dark:text-zinc-300">{wh.utilization}%</span>
            </div>
            <div className="h-1.5 w-full bg-zinc-150 dark:bg-zinc-800 rounded-full overflow-hidden border border-zinc-200/40 dark:border-zinc-700">
              <div className={`h-full ${
                wh.utilization > 80 ? "bg-red-500" : wh.utilization > 50 ? "bg-amber-500" : "bg-zinc-800 dark:bg-zinc-300"
              }`} style={{ width: `${wh.utilization}%` }} />
            </div>
            <div className="pt-1 flex justify-between text-[10px] font-mono text-zinc-400 dark:text-zinc-500">
              <span>SKU: {wh.total_items} Classes</span>
              <span>Stock: {wh.total_units.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>

      {/* TRANSFERS AS CARDS */}
      <div className="space-y-4">
        <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Transfer Options</span>
        {data.suggested_transfers.length === 0 ? (
          <div className="space-y-6">
            {/* Balanced Status Banner */}
            <div className="bg-muted border border-muted p-6 rounded-lg text-center space-y-2 transition-standard hover:scale-105">
              <span className="inline-block px-2.5 py-0.5 rounded bg-green-950/30 text-[#22C55E] border border-green-900/50 text-[10px] font-mono font-bold uppercase">
                Status: Fully Balanced
              </span>
              <h4 className="text-sm font-bold text-white font-mono uppercase">All Warehouse Nodes Balanced</h4>
              <p className="text-xs text-zinc-400 max-w-md mx-auto">
                Safety stock levels are optimized across all locations. No inter-warehouse stock transfers are currently required.
              </p>
            </div>

            {/* Network Summary & Network Totals Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Network Utilization Summary */}
              <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
                <h4 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">Network Utilization Summary</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-zinc-500">Total Capacity:</span>
                    <span className="text-zinc-350 font-bold">{netCapacity.toLocaleString()} units</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-zinc-500">Total Units:</span>
                    <span className="text-zinc-350 font-bold">{netUnits.toLocaleString()} units</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono border-t border-[#27272A] pt-2">
                    <span className="text-zinc-400">Average Utilization:</span>
                    <span className="text-[#DC2626] font-extrabold">{netUtilization}%</span>
                  </div>
                </div>
                {/* Progress bar */}
                <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden border border-zinc-700">
                  <div className="h-full bg-error" style={{ width: `${netUtilization}%` }} />
                </div>
              </div>

              {/* Network Totals */}
              <div className="bg-[#18181B] border border-[#27272A] p-6 rounded-lg space-y-4">
                <h4 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">Network Totals</h4>
                <div className="grid grid-cols-3 gap-2 text-center pt-2">
                  <div className="p-3 bg-[#09090B] border border-[#27272A] rounded">
                    <span className="text-[9px] font-mono text-zinc-500 uppercase block">Total Value</span>
                    <span className="text-xs font-bold text-white mt-1 block">₹{netValue.toLocaleString()}</span>
                  </div>
                  <div className="p-3 bg-[#09090B] border border-[#27272A] rounded">
                    <span className="text-[9px] font-mono text-zinc-500 uppercase block">SKU Classes</span>
                    <span className="text-xs font-bold text-white mt-1 block">{netSkuClasses}</span>
                  </div>
                  <div className="p-3 bg-[#09090B] border border-[#27272A] rounded">
                    <span className="text-[9px] font-mono text-zinc-500 uppercase block">Nodes</span>
                    <span className="text-xs font-bold text-white mt-1 block">{netWarehouses}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Warehouse Health Cards */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono font-bold text-zinc-400 uppercase tracking-wider">Warehouse Health Status</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {data.warehouses.map((wh: any) => {
                  const healthState = wh.utilization > 80 ? "Critical" : wh.utilization > 50 ? "Warning" : "Healthy";
                  const healthColor = wh.utilization > 80 
                    ? "text-error bg-error/10 border-error/20" 
                    : wh.utilization > 50 
                    ? "text-primary bg-primary/10 border-primary/20" 
                    : "text-success bg-success/10 border-success/20";
                  return (
                    <div key={wh.id} className="bg-muted border border-muted p-5 rounded-lg space-y-3 transition-standard hover:scale-105">
                      <div className="flex justify-between items-start">
                        <div>
                          <h5 className="font-bold text-white text-sm">{wh.name}</h5>
                          <span className="text-[10px] font-mono text-zinc-500 uppercase">{wh.location}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold border ${healthColor}`}>
                          {healthState}
                        </span>
                      </div>
                      <div className="pt-2 border-t border-[#27272A] space-y-1 text-[11px] font-mono text-zinc-400">
                        <div className="flex justify-between">
                          <span>Inventory Count:</span>
                          <span className="text-white font-medium">{wh.total_units.toLocaleString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Utilization:</span>
                          <span className="text-white font-medium">{wh.utilization}%</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.suggested_transfers.map((t: any, idx: number) => {
              const transferKey = `${t.sku}-${t.from_warehouse}-${t.to_warehouse}`;
              const isSubmitting = submittingTransferSku === transferKey;
              return (
                <div key={idx} className="bg-surface border border-muted p-6 rounded-lg flex flex-col justify-between gap-4 hover:border-muted dark:hover:border-muted transition-standard hover:scale-105 shadow-sm">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-xs font-bold text-zinc-450 dark:text-zinc-500">{t.sku}</span>
                      <span className="text-sm font-mono font-bold text-green-600 dark:text-green-400 font-sans">Saves ₹{t.financial_impact.toLocaleString()}</span>
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-zinc-955 dark:text-zinc-50 leading-snug">{t.product_name}</h3>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 font-sans font-medium">{t.reason}</p>
                    </div>
                    <div className="pt-2 border-t border-zinc-800 flex justify-between items-center text-[10px] font-mono text-zinc-500">
                      <span>Route</span>
                      <span className="text-zinc-800 dark:text-zinc-200 font-semibold">{t.from_warehouse} ➔ {t.to_warehouse}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleTransfer(t)}
                    disabled={!!submittingTransferSku}
                    className="w-full py-2.5 bg-surface hover:bg-muted dark:bg-error dark:hover:bg-[#B91C1C] dark:text-white text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-standard disabled:opacity-50"
                  >
                    {isSubmitting ? "Transferring..." : `Transfer ${t.quantity} Units`}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

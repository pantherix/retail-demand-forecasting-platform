import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

export default function WarehouseView() {
  const { refreshTrigger, triggerRefresh, setActiveSku, setActiveTab } = useStore();
  const { addToast } = useToast();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Submitting tracker for specific transfers
  const [submittingTransferSku, setSubmittingTransferSku] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getWarehouses()
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
  }, [refreshTrigger]);

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
          <div key={wh.id} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-5 rounded-lg space-y-3 shadow-sm">
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
          <EmptyState
            title="All warehouse nodes balanced"
            description="The Warehouse Network shows that all safety levels are locally optimized. No inter-warehouse inventory transfers suggested at this time."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.suggested_transfers.map((t: any, idx: number) => {
              const transferKey = `${t.sku}-${t.from_warehouse}-${t.to_warehouse}`;
              const isSubmitting = submittingTransferSku === transferKey;
              return (
                <div key={idx} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 rounded-lg flex flex-col justify-between gap-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors shadow-sm">
                  <div className="space-y-3">
                    <div className="flex justify-between items-start">
                      <span className="font-mono text-xs font-bold text-zinc-450 dark:text-zinc-500">{t.sku}</span>
                      <span className="text-sm font-mono font-bold text-green-600 dark:text-green-400 font-sans">Saves ₹{t.financial_impact.toLocaleString()}</span>
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-zinc-955 dark:text-zinc-50 leading-snug">{t.product_name}</h3>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 font-sans font-medium">{t.reason}</p>
                    </div>
                    <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex justify-between items-center text-[10px] font-mono text-zinc-500">
                      <span>Route</span>
                      <span className="text-zinc-800 dark:text-zinc-200 font-semibold">{t.from_warehouse} ➔ {t.to_warehouse}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleTransfer(t)}
                    disabled={!!submittingTransferSku}
                    className="w-full py-2.5 bg-zinc-955 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-955 text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-colors disabled:opacity-50"
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

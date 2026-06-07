import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

export default function ReorderEngineView() {
  const { refreshTrigger, triggerRefresh, setActiveSku, setActiveTab } = useStore();
  const { addToast } = useToast();

  const [reorders, setReorders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Submitting tracker for specific SKU reorder approvals
  const [submittingSku, setSubmittingSku] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getReorder()
      .then((res) => {
        setReorders(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load reorders list.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  // OPTIMISTIC ACTIONS: handleApproveReorder (reorder approval)
  const handleApproveReorder = async (sku: string, qty: number) => {
    if (submittingSku) return;
    setSubmittingSku(sku);

    const originalReorders = [...reorders];

    // Optimistically set the recommended quantity to 0
    setReorders(prev => prev.map(r => r.sku === sku ? { ...r, recommended_reorder_qty: 0, current_stock: r.current_stock + qty } : r));

    try {
      const skuData = await api.getSKU(sku);
      const supplier_id = skuData.supplier_id || 3;
      await api.createPurchaseOrder({
        supplier_id,
        items: [{ sku, quantity: qty }]
      });
      const pos = await api.getPurchaseOrders();
      const latestDraft = pos.find((p: any) => p.status === "Draft");
      if (latestDraft) {
        await api.approvePurchaseOrder(latestDraft.id);
        addToast(`Fulfillment replenishment ordered for SKU ${sku}.`, "success");
        triggerRefresh();
      } else {
        throw new Error("Failed to auto-draft purchase order");
      }
    } catch (err: any) {
      // Rollback on failure
      setReorders(originalReorders);
      addToast(err.message || "Reorder approval failed", "error");
    } finally {
      setSubmittingSku(null);
    }
  };

  // Memoize active orders and top order
  const activeOrders = useMemo(() => {
    return reorders
      .filter((r: any) => r.recommended_reorder_qty > 0)
      .sort((a, b) => b.revenue_exposure - a.revenue_exposure);
  }, [reorders]);

  const topOrder = useMemo(() => {
    return activeOrders[0];
  }, [activeOrders]);

  if (loading && reorders.length === 0) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 py-2">
        <CardSkeleton />
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

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-2">
      {topOrder && (
        <div className="space-y-4">
          <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Critical Replenishment Required</span>
          <HeroActionCard
            title={`Order ${topOrder.recommended_reorder_qty.toLocaleString()} units for SKU ${topOrder.sku}`}
            description={`${topOrder.product_name} stockout will trigger soon. Order immediately to protect ₹${topOrder.revenue_exposure.toLocaleString()} in revenue.`}
            actionLabel={`LOW COVERAGE: ${topOrder.days_of_cover} DAYS`}
            buttonText={submittingSku === topOrder.sku ? "Approving..." : "Approve PO"}
            colorClass="border-red-500"
            disabled={!!submittingSku}
            onExecute={() => handleApproveReorder(topOrder.sku, topOrder.recommended_reorder_qty)}
            onSkuClick={() => { setActiveSku(topOrder.sku); setActiveTab("product-intelligence"); }}
          />
        </div>
      )}

      {/* ALL REORDERS AS CARDS */}
      <div className="space-y-4">
        <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Replenishment Opportunities</span>
        {reorders.length === 0 ? (
          <EmptyState
            title="All inventory coverage secure"
            description="The Reorder Engine reports that safety stocks and current supply pipelines satisfy all localized demand constraints. No orders needed."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {reorders.map((item) => (
              <div key={item.sku} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 rounded-lg flex flex-col justify-between gap-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors shadow-sm">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <span className="font-mono text-xs font-bold text-zinc-450 dark:text-zinc-500">{item.sku}</span>
                    <span className="text-xs font-mono font-bold text-zinc-500">Cover: <strong className={item.days_of_cover < 7 ? "text-red-600 dark:text-red-400 font-bold" : "text-zinc-800 dark:text-zinc-300 font-medium"}>{item.days_of_cover}d</strong></span>
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-955 dark:text-zinc-50 leading-snug">{item.product_name}</h3>
                  </div>

                  <div className="grid grid-cols-2 gap-3 pt-2 border-t border-zinc-100 dark:border-zinc-800 font-mono text-[10px] text-zinc-500">
                    <div>
                      <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">ROP Point</span>
                      <span className="text-zinc-900 dark:text-zinc-200 font-semibold">{item.reorder_point.toLocaleString()} units</span>
                    </div>
                    <div>
                      <span className="block uppercase text-[8px] text-zinc-400 dark:text-zinc-500">Current Stock</span>
                      <span className="text-zinc-950 dark:text-zinc-50 font-bold">{item.current_stock.toLocaleString()} units</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex justify-between items-center text-xs">
                    <span className="text-zinc-400 dark:text-zinc-500 font-mono text-[10px] uppercase">Exposure protected</span>
                    <span className="font-bold text-zinc-900 dark:text-zinc-50 font-mono">₹{item.revenue_exposure.toLocaleString()}</span>
                  </div>
                </div>

                {item.recommended_reorder_qty > 0 ? (
                  <button
                    onClick={() => handleApproveReorder(item.sku, item.recommended_reorder_qty)}
                    disabled={!!submittingSku}
                    className="w-full py-2.5 bg-zinc-955 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-950 text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-colors disabled:opacity-50"
                  >
                    {submittingSku === item.sku ? "Approving..." : `Approve Order (${item.recommended_reorder_qty})`}
                  </button>
                ) : (
                  <div className="py-2.5 text-center bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/80 dark:border-zinc-800 rounded text-zinc-400 dark:text-zinc-500 font-mono text-[10px] uppercase font-bold">
                    Coverage Secure
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

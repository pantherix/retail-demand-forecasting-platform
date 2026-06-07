import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import { HeroActionCard } from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { EmptyState } from "../ui/EmptyState";
import { ErrorState } from "../ui/ErrorState";

export default function PurchaseOrderView() {
  const { refreshTrigger, triggerRefresh } = useStore();
  const { addToast } = useToast();

  const [pos, setPos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Submitting tracker for specific PO approval actions
  const [submittingPoId, setSubmittingPoId] = useState<number | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    api.getPurchaseOrders()
      .then((res) => {
        setPos(res);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load purchase orders ledger.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  // OPTIMISTIC ACTIONS: handleApprove (PO approval)
  const handleApprove = async (id: number) => {
    if (submittingPoId !== null) return;
    setSubmittingPoId(id);

    const originalPos = [...pos];

    // Optimistically update status to Ordered
    setPos(prev => prev.map(po => po.id === id ? { ...po, status: "Ordered" } : po));

    try {
      await api.approvePurchaseOrder(id);
      addToast(`PO Approved. Dispatch pipeline synced.`, "success");
      triggerRefresh();
    } catch (err: any) {
      // Rollback on failure
      setPos(originalPos);
      addToast(err.message || "PO approval failed", "error");
    } finally {
      setSubmittingPoId(null);
    }
  };

  // Memoize pending POs and top PO
  const pendingPOs = useMemo(() => {
    return pos
      .filter(po => po.status === "Draft" || po.status === "Pending Approval")
      .sort((a, b) => b.total_cost - a.total_cost);
  }, [pos]);

  const topPO = useMemo(() => {
    return pendingPOs[0];
  }, [pendingPOs]);

  if (loading && pos.length === 0) {
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
      {topPO && (
        <div className="space-y-4">
          <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-widest block">Capital Approval Pending</span>
          <HeroActionCard
            title={`Approve PO-${topPO.id} to ${topPO.supplier_name}`}
            description={`Purchase authorization requires signature for ₹${topPO.total_cost.toLocaleString()}. PO details: ${topPO.details.map((d: any) => `${d.sku} (x${d.quantity})`).join(", ")}.`}
            actionLabel="PENDING SIGN-OFF"
            buttonText={submittingPoId === topPO.id ? "Authorizing..." : "Authorize PO"}
            colorClass="border-amber-500"
            disabled={submittingPoId !== null}
            onExecute={() => handleApprove(topPO.id)}
          />
        </div>
      )}

      {/* PO LEDGER AS CARDS */}
      <div className="space-y-4">
        <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-widest block">Purchase Orders Ledger</span>
        {pos.length === 0 ? (
          <EmptyState
            title="Purchase orders ledger empty"
            description="No current purchase orders have been drafted. Approve reorders or create orders in the Action Center."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pos.map((po) => (
              <div key={po.id} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 p-6 rounded-lg flex flex-col justify-between gap-4 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors shadow-sm">
                <div className="space-y-3">
                  <div className="flex justify-between items-start">
                    <span className="font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">PO-{po.id}</span>
                    <span className="text-sm font-mono font-bold text-zinc-900 dark:text-zinc-50 font-sans">₹{po.total_cost.toLocaleString()}</span>
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-zinc-955 dark:text-zinc-50 leading-snug">{po.supplier_name}</h3>
                    <div className="mt-2 space-y-1 text-xs text-zinc-550 dark:text-zinc-400 font-mono">
                      {po.details.map((d: any, idx: number) => (
                        <span key={idx} className="block">
                          {d.sku}: {d.quantity.toLocaleString()} units @ ₹{d.unit_cost.toLocaleString()}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800 flex justify-between items-center text-[10px] font-mono text-zinc-500">
                    <span>Status</span>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                      po.status === "Draft" ? "bg-zinc-50 dark:bg-zinc-950 text-zinc-505 dark:text-zinc-400 border-zinc-200 dark:border-zinc-800" :
                      po.status === "Ordered" || po.status === "In Transit" ? "bg-amber-50 dark:bg-amber-955/20 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-900/40" :
                      "bg-green-50 dark:bg-green-955/20 text-green-600 dark:text-green-400 border-green-200 dark:border-green-900/40"
                    }`}>
                      {po.status}
                    </span>
                  </div>
                </div>

                {po.status === "Draft" || po.status === "Pending Approval" ? (
                  <button
                    onClick={() => handleApprove(po.id)}
                    disabled={submittingPoId !== null}
                    className="w-full py-2.5 bg-zinc-955 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 dark:text-zinc-955 text-white font-mono text-xs uppercase font-bold tracking-wider rounded cursor-pointer transition-colors disabled:opacity-50"
                  >
                    {submittingPoId === po.id ? "Approving..." : "Approve & Order"}
                  </button>
                ) : (
                  <div className="py-2.5 text-center bg-zinc-50 dark:bg-zinc-950 border border-zinc-200/80 dark:border-zinc-800 rounded text-zinc-400 dark:text-zinc-500 font-mono text-[10px] uppercase font-bold">
                    Ordered
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

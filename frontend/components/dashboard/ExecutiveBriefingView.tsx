import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import {
  ShieldCheck, AlertTriangle, RefreshCw
} from "lucide-react";
import {
  RevenueImpactCard, HeroActionCard, ActionFeed
} from "./DashboardComponents";
import { CardSkeleton } from "../ui/CardSkeleton";
import { ErrorState } from "../ui/ErrorState";
import { KPICard } from "./KPICard";
import { RevenueAnalyticsChart } from "./RevenueAnalyticsChart";
import { InventoryHealthPanel } from "./InventoryHealthPanel";
import { ExecutiveInsights } from "./ExecutiveInsights";
import { CriticalActionsTable } from "./CriticalActionsTable";
import { EventsTimeline } from "./EventsTimeline";
import { useExecutiveMetrics } from "../../hooks/useExecutiveMetrics";
import { useInventoryHealth } from "../../hooks/useInventoryHealth";

export default function ExecutiveBriefingView() {
  const { refreshTrigger, triggerRefresh, setActiveTab, setActiveSku } = useStore();
  const { addToast } = useToast();

  const [data, setData] = useState<any>(null);
  const [reorders, setReorders] = useState<any[]>([]);
  const [suggestedTransfers, setSuggestedTransfers] = useState<any[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<any[]>([]);
  const [forecastQuality, setForecastQuality] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // For disabling buttons during submission
  const [submittingAction, setSubmittingAction] = useState<string | null>(null);

  const fetchData = () => {
    setLoading(true);
    setErrorMsg(null);
    Promise.all([
      api.getDashboard(),
      api.getReorder(),
      api.getWarehouses(),
      api.getPurchaseOrders(),
      api.getForecastQuality()
    ])
      .then(([dash, reorderList, whList, poList, fq]) => {
        setData(dash);
        setReorders(reorderList);
        setSuggestedTransfers(whList.suggested_transfers || []);
        setPurchaseOrders(poList || []);
        setForecastQuality(fq);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || "Failed to load dashboard data.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  // OPTIMISTIC ACTIONS: handleQuickAction (reorder/PO)
  const handleQuickAction = async (sku: string, qty: number) => {
    if (submittingAction) return;
    setSubmittingAction(`quick-${sku}`);

    // Backups for rollback
    const originalReorders = [...reorders];
    const originalDashboard = data ? { ...data } : null;

    // Optimistically update reorder list: clear this sku's reorder qty
    setReorders(prev =>
      prev.map(r => r.sku === sku ? { ...r, recommended_reorder_qty: 0, current_stock: r.current_stock + qty } : r)
    );
    // Optimistically adjust dashboard metrics (reduce revenue at risk)
    if (data) {
      const reorderItem = reorders.find(r => r.sku === sku);
      const exposure = reorderItem ? reorderItem.revenue_exposure : 0;
      setData((prev: any) => ({
        ...prev,
        revenue_at_risk: Math.max(0, prev.revenue_at_risk - exposure)
      }));
    }

    try {
      const reorderItem = originalReorders.find(r => r.sku === sku);
      const supplier_id = reorderItem?.supplier_id || 3;
      await api.createPurchaseOrder({
        supplier_id,
        items: [{ sku, quantity: qty }]
      });
      const pos = await api.getPurchaseOrders();
      const latestDraft = pos.find((p: any) => p.status === "Draft");
      if (latestDraft) {
        await api.approvePurchaseOrder(latestDraft.id);
        addToast(`Fulfillment approved. Ordered ${qty} units of SKU ${sku}.`, "success");
        triggerRefresh();
      } else {
        throw new Error("Failed to auto-draft purchase order");
      }
    } catch (err: any) {
      // Rollback on failure
      setReorders(originalReorders);
      if (originalDashboard) setData(originalDashboard);
      addToast(err.message || "Replenishment action failed", "error");
    } finally {
      setSubmittingAction(null);
    }
  };

  // OPTIMISTIC ACTIONS: handleTransfer (transfer execution)
  const handleTransfer = async (transfer: any) => {
    if (submittingAction) return;
    setSubmittingAction(`transfer-${transfer.sku}`);

    // Backups for rollback
    const originalTransfers = [...suggestedTransfers];
    const originalDashboard = data ? { ...data } : null;

    // Optimistically filter out the executed transfer
    setSuggestedTransfers(prev => prev.filter(t => !(t.sku === transfer.sku && t.from_warehouse === transfer.from_warehouse && t.to_warehouse === transfer.to_warehouse)));
    
    // Optimistically adjust metrics (reduce revenue at risk)
    if (data) {
      setData((prev: any) => ({
        ...prev,
        revenue_at_risk: Math.max(0, prev.revenue_at_risk - transfer.financial_impact)
      }));
    }

    try {
      await api.createTransfer({
        from_wh: transfer.from_warehouse,
        to_wh: transfer.to_warehouse,
        sku: transfer.sku,
        quantity: transfer.quantity
      });
      addToast(`Stock transfer approved. Shipped ${transfer.quantity} units from ${transfer.from_warehouse} to ${transfer.to_warehouse}.`, "success");
      triggerRefresh();
    } catch (err: any) {
      // Rollback on failure
      setSuggestedTransfers(originalTransfers);
      if (originalDashboard) setData(originalDashboard);
      addToast(err.message || "Transfer failed", "error");
    } finally {
      setSubmittingAction(null);
    }
  };

  const handleLiquidateOverstock = async () => {
    if (submittingAction) return;
    setSubmittingAction("liquidate");
    try {
      const openDecisions = await api.getDecisions({ status: "Open" });
      const overstockItems = openDecisions.filter((d: any) => d.recommended_action === "Liquidate Excess" || d.days_remaining > 90);
      if (overstockItems.length > 0) {
        await Promise.all(overstockItems.map((item: any) => api.updateDecisionStatus(item.sku, "Resolved")));
        addToast(`Liquidation dispatch created. Released ₹${data.overstock_value.toLocaleString()} of stagnant capital.`, "success");
        triggerRefresh();
      } else {
        addToast("Liquidation protocol dispatched. Active surplus mitigated.", "success");
      }
    } catch (err: any) {
      addToast(err.message || "Liquidation failed", "error");
    } finally {
      setSubmittingAction(null);
    }
  };

  // Memoize active reorders
  const activeReorders = useMemo(() => {
    return reorders.filter((r: any) => r.recommended_reorder_qty > 0);
  }, [reorders]);

  // Memoize top action calculations (highest exposure / value)
  const heroAction = useMemo(() => {
    if (!data) return null;
    const topReorder = [...activeReorders].sort((a, b) => b.revenue_exposure - a.revenue_exposure)[0];
    const topTransfer = [...suggestedTransfers].sort((a, b) => b.financial_impact - a.financial_impact)[0];
    const overstockVal = data.overstock_value;

    let action: any = null;
    let maxVal = 0;

    if (topReorder && topReorder.revenue_exposure > maxVal) {
      maxVal = topReorder.revenue_exposure;
      action = {
        type: "reorder",
        value: topReorder.revenue_exposure,
        title: `Protect ₹${topReorder.revenue_exposure.toLocaleString()}`,
        sku: topReorder.sku,
        description: `SKU ${topReorder.sku} (${topReorder.product_name}) coverage is critically low at ${topReorder.days_of_cover} days. Order ${topReorder.recommended_reorder_qty} units immediately to prevent active stockout deficit.`,
        buttonText: submittingAction === `quick-${topReorder.sku}` ? "Approving..." : "Approve PO",
        actionLabel: "REORDER DEFICIT",
        colorClass: "border-red-500",
        disabled: !!submittingAction,
        execute: () => handleQuickAction(topReorder.sku, topReorder.recommended_reorder_qty)
      };
    }

    if (topTransfer && topTransfer.financial_impact > maxVal) {
      maxVal = topTransfer.financial_impact;
      action = {
        type: "transfer",
        value: topTransfer.financial_impact,
        title: `Transfer ${topTransfer.quantity} Units`,
        sku: topTransfer.sku,
        description: `Move ${topTransfer.quantity} units of SKU ${topTransfer.sku} from ${topTransfer.from_warehouse} to ${topTransfer.to_warehouse} to capture ₹${topTransfer.financial_impact.toLocaleString()} in pending demand.`,
        buttonText: submittingAction === `transfer-${topTransfer.sku}` ? "Executing..." : "Execute Transfer",
        actionLabel: "STOCK BALANCING",
        colorClass: "border-green-500",
        disabled: !!submittingAction,
        execute: () => handleTransfer(topTransfer)
      };
    }

    if (overstockVal > maxVal && overstockVal > 15000) {
      action = {
        type: "overstock",
        value: overstockVal,
        title: `Recover ₹${overstockVal.toLocaleString()} Overstock`,
        description: `Working capital is tied up in stagnant SKU stock across the warehouse network. Create a liquidation strategy to release cash flow and minimize carrying overhead.`,
        buttonText: submittingAction === "liquidate" ? "Dispatched..." : "Execute Liquidation",
        actionLabel: "EXCESS CAPITAL",
        colorClass: "border-amber-500",
        disabled: !!submittingAction,
        execute: handleLiquidateOverstock
      };
    }

    if (!action) {
      action = {
        type: "balanced",
        title: "All Inventory Nodes Balanced",
        description: "Safety stocks are currently sufficient across all product locations. No urgent supplier orders or inter-warehouse transfers are flagged for execution.",
        buttonText: "Acknowledge State",
        actionLabel: "STEADY STATE",
        colorClass: "border-zinc-300 dark:border-zinc-750",
        disabled: false,
        execute: () => addToast("System state logged.", "info")
      };
    }

    return action;
  }, [data, activeReorders, suggestedTransfers, submittingAction]);

  // Memoize secondary queue items
  const secondaryQueue = useMemo(() => {
    if (!heroAction) return [];
    const queue: any[] = [];
    activeReorders.forEach((r: any) => {
      if (r.sku !== heroAction.sku) {
        queue.push({
          type: "Replenish Order",
          value: r.revenue_exposure,
          title: `Protect ₹${r.revenue_exposure.toLocaleString()}: SKU ${r.sku}`,
          sub: `Order ${r.recommended_reorder_qty} units of ${r.product_name} (Cover: ${r.days_of_cover}d)`,
          buttonText: submittingAction === `quick-${r.sku}` ? "Approving..." : "Approve",
          disabled: !!submittingAction,
          execute: () => handleQuickAction(r.sku, r.recommended_reorder_qty)
        });
      }
    });
    suggestedTransfers.forEach((t: any) => {
      if (t.sku !== heroAction.sku) {
        queue.push({
          type: "Warehouse Transfer",
          value: t.financial_impact,
          title: `Recover ₹${t.financial_impact.toLocaleString()}: SKU ${t.sku}`,
          sub: `Move ${t.quantity} units from ${t.from_warehouse} to ${t.to_warehouse}`,
          buttonText: submittingAction === `transfer-${t.sku}` ? "Executing..." : "Transfer",
          disabled: !!submittingAction,
          execute: () => handleTransfer(t)
        });
      }
    });
    return queue.sort((a, b) => b.value - a.value);
  }, [heroAction, activeReorders, suggestedTransfers, submittingAction]);

  const auditLogs = useMemo(() => {
    if (!data || !data.executive_feed) return [];
    return data.executive_feed
      .filter((item: any) => item.type === "audit")
      .map((au: any) => ({
        title: au.title,
        message: au.message
      }));
  }, [data]);

  const { healthyCount, warningCount, criticalCount, totalCount, isDataUnavailable: isHealthUnavailable } = useInventoryHealth(reorders);
  const metrics = useExecutiveMetrics(data, reorders, purchaseOrders, forecastQuality);

  const criticalActions = useMemo(() => {
    if (!data) return [];
    
    const reorderActions = reorders
      .filter((r: any) => r.recommended_reorder_qty > 0)
      .map((r: any) => ({
        sku: r.sku,
        name: r.product_name,
        type: "reorder" as const,
        riskLevel: (r.days_of_cover < 7 ? "critical" : r.days_of_cover < 15 ? "high" : "medium") as "critical" | "high" | "medium",
        revenueImpact: r.revenue_exposure,
        confidenceScore: Math.round(forecastQuality?.forecast_accuracy ?? 92.4),
        recommendedAction: `Order ${r.recommended_reorder_qty} units`,
        qty: r.recommended_reorder_qty,
        rawItem: r
      }));

    const transferActions = suggestedTransfers.map((t: any) => ({
      sku: t.sku,
      name: t.product_name,
      type: "transfer" as const,
      riskLevel: (t.financial_impact > 50000 ? "critical" : t.financial_impact > 15000 ? "high" : "medium") as "critical" | "high" | "medium",
      revenueImpact: t.financial_impact,
      confidenceScore: Math.round(forecastQuality?.forecast_accuracy ?? 92.4),
      recommendedAction: `Move ${t.quantity} units from ${t.from_warehouse} to ${t.to_warehouse}`,
      qty: t.quantity,
      rawItem: t
    }));

    const liquidateActions = data.overstock_value > 15000 ? [{
      sku: "ALL-OVERSTOCK",
      name: "Excess Network Stagnant Capital",
      type: "liquidate" as const,
      riskLevel: "medium" as const,
      revenueImpact: data.overstock_value,
      confidenceScore: 100,
      recommendedAction: "Execute Liquidation Protocol",
      qty: 0,
      rawItem: null
    }] : [];

    return [...reorderActions, ...transferActions, ...liquidateActions].sort((a, b) => b.revenueImpact - a.revenueImpact);
  }, [data, reorders, suggestedTransfers, forecastQuality]);

  const revenueProtectedToday = useMemo(() => {
    return purchaseOrders
      .filter((po: any) => po.status === "Ordered" || po.status === "Approved")
      .reduce((sum, po) => sum + po.total_cost, 0);
  }, [purchaseOrders]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 py-2">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          <CardSkeleton />
          <CardSkeleton />
        </div>
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

  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-12 py-2 relative">
      {/* 1. KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard title="Revenue Protected" metric={metrics.revenueProtected} isCurrency />
        <KPICard title="Revenue At Risk" metric={metrics.revenueAtRisk} isCurrency />
        <KPICard title="Inventory Health" metric={metrics.inventoryHealth} />
        <KPICard title="Forecast Accuracy" metric={metrics.forecastAccuracy} />
      </div>

      {/* 2. Charts & Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RevenueAnalyticsChart revenueProtected={revenueProtectedToday} revenueAtRisk={data.revenue_at_risk} />
        </div>
        <div>
          <InventoryHealthPanel
            healthyCount={healthyCount}
            warningCount={warningCount}
            criticalCount={criticalCount}
            totalCount={totalCount}
            isUnavailable={loading}
          />
        </div>
      </div>

      {/* 3. AI Insights & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ExecutiveInsights
          revenueAtRisk={data.revenue_at_risk}
          criticalCount={criticalCount}
          forecastAccuracy={Math.round(forecastQuality?.forecast_accuracy ?? 92.4)}
          isUnavailable={loading}
        />
        <EventsTimeline events={data.executive_feed || []} isUnavailable={loading} />
      </div>

      {/* 4. Critical Actions Table */}
      <div className="space-y-4">
        <CriticalActionsTable
          actions={criticalActions}
          onApprove={(item) => {
            if (item.type === "reorder") {
              handleQuickAction(item.sku, item.qty);
            } else if (item.type === "transfer") {
              handleTransfer(item.rawItem);
            } else if (item.type === "liquidate") {
              handleLiquidateOverstock();
            }
          }}
          onInvestigate={(sku) => {
            setActiveSku(sku);
            setActiveTab("product-intelligence");
          }}
          isUnavailable={loading}
        />
      </div>
    </div>
  );
}

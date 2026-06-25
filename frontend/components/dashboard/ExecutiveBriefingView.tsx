"use client";

import { useEffect, useState } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useToast } from "../../hooks/useToast";
import {
  AlertTriangle, RefreshCw, ShoppingBag, Landmark, Sparkles, Check, Loader2, FileCheck, ShieldAlert
} from "lucide-react";

export default function ExecutiveBriefingView() {
  const { refreshTrigger, triggerRefresh } = useStore();
  const { addToast } = useToast();

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actioningSku, setActioningSku] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const dash = await api.getDashboard();
      setData(dash);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load executive briefing exceptions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [refreshTrigger]);

  const handleAutogeneratePO = async (sku: string, shortageQty: number, supplierId: number) => {
    if (actioningSku) return;
    setActioningSku(sku);
    
    // Order quantity: at least 50 units, or shortage * 2 to cover lead time
    const orderQty = Math.max(50, Math.ceil(shortageQty * 2.0));
    addToast(`Initiating emergency procurement for SKU ${sku}...`, "info");
    
    try {
      const res = await api.autogeneratePO({
        sku,
        quantity: orderQty,
        supplier_id: supplierId || 1
      });
      
      if (res.success) {
        addToast(`Emergency PO generated & Approved! Ordered ${orderQty} units.`, "success");
        triggerRefresh();
      } else {
        throw new Error("Failed to auto-generate PO.");
      }
    } catch (err: any) {
      addToast(err.message || "Emergency PO generation failed.", "error");
    } finally {
      setActioningSku(null);
    }
  };

  const formatCurrency = (val: number | undefined) => {
    return (val ?? 0).toLocaleString("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    });
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center py-20 space-y-4">
        <RefreshCw className="h-10 w-10 text-red-600 animate-spin" />
        <p className="text-zinc-400 text-xs font-mono">LOADING COMMAND FEED...</p>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className="border border-red-500/20 bg-red-950/10 p-8 rounded-xl text-center space-y-4 max-w-lg mx-auto mt-12">
        <AlertTriangle className="h-10 w-10 text-red-500 mx-auto" />
        <h3 className="font-bold text-white text-base font-mono">CRITICAL API RECOVERY ERROR</h3>
        <p className="text-xs text-zinc-400 leading-relaxed">{errorMsg}</p>
        <button
          onClick={fetchData}
          className="px-4 py-2 border border-[#27272A] hover:bg-[#09090B] text-zinc-300 rounded text-xs transition-colors font-mono cursor-pointer"
        >
          RETRY CONFLICT RESOLUTION
        </button>
      </div>
    );
  }

  const revenueDisplay = data?.total_revenue_at_risk ?? data?.totalRevenueAtRisk ?? 0;
  const exceptionDisplay = data?.exceptions_count ?? data?.exceptionsCount ?? 0;
  const exceptions = data?.exceptions ?? [];

  return (
    <div className="ferrari-panel p-8 space-y-8 text-zinc-100 font-sans shadow-2xl relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-[#E10600]/5 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-[#E10600]/5 rounded-full blur-[150px] pointer-events-none" />
      {/* Glossy reflection layer */}
      <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-white/10 pb-6 relative z-10">
        <div>
          <h2 className="text-xl font-mono font-bold tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-red-600" /> SUPPLY CHAIN COMMAND DECK
          </h2>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time automated runout prediction scanning. Showing items requiring emergency replenishment.
          </p>
        </div>
        <div>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-1.5 border border-white/10 bg-white/5 hover:bg-white/10 text-zinc-300 rounded text-xs transition-all font-mono cursor-pointer"
          >
            <RefreshCw className="h-3.5 w-3.5" /> REFRESH STATE
          </button>
        </div>
      </div>


      {/* 3-Box KPI Metric Strip */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
        {/* Box 1: Revenue at Risk */}
        <div className="bg-black/30 border border-red-500/20 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group">
          <div className="space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Total Revenue Exposure</span>
            <h3 className="text-2xl font-bold font-mono text-red-500">
              {formatCurrency(revenueDisplay)}
            </h3>
            <p className="text-[10px] text-zinc-500">Value of shortage quantities times unit price</p>
          </div>
          <div className="h-10 w-10 bg-red-950/20 border border-red-500/30 rounded flex items-center justify-center text-red-400">
            <Landmark className="h-5 w-5" />
          </div>
        </div>

        {/* Box 2: Profit at Risk */}
        <div className="bg-black/30 border border-amber-500/20 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group">
          <div className="space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Total Profit Margin Exposure</span>
            <h3 className="text-2xl font-bold font-mono text-amber-500">
              {formatCurrency(data?.total_profit_at_risk)}
            </h3>
            <p className="text-[10px] text-zinc-500">Marginal exposure at stake downstream</p>
          </div>
          <div className="h-10 w-10 bg-amber-950/20 border border-amber-500/30 rounded flex items-center justify-center text-amber-400">
            <ShoppingBag className="h-5 w-5" />
          </div>
        </div>

        {/* Box 3: Exceptions Count */}
        <div className="bg-black/30 border border-white/5 p-5 rounded-lg flex items-center justify-between shadow-lg relative overflow-hidden group">
          <div className="space-y-1.5">
            <span className="text-[10px] font-mono text-zinc-400 tracking-wider uppercase">Failing SKU Nodes</span>
            <h3 className="text-2xl font-bold font-mono text-white">
              {exceptionDisplay}
            </h3>
            <p className="text-[10px] text-zinc-500">Nodes where Cover Days &lt; Lead Time</p>
          </div>
          <div className="h-10 w-10 bg-zinc-900 border border-white/5 rounded flex items-center justify-center text-red-600">
            <AlertTriangle className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Exceptions Feed Header */}
      <div className="space-y-4 relative z-10">
        <h3 className="text-xs font-mono font-bold tracking-widest text-red-600 uppercase">
          Predictive Runout Exception Feed
        </h3>

        {exceptions.length === 0 ? (
          <div className="bg-black/30 border border-emerald-500/20 p-10 rounded-lg text-center space-y-2">
            <FileCheck className="h-8 w-8 text-emerald-400 mx-auto" />
            <h4 className="font-bold text-sm text-white font-mono">SUPPLY CHAIN IN BALANCE</h4>
            <p className="text-xs text-zinc-500 max-w-xs mx-auto">
              All warehouse product stocking covers lead time delays safely. No critical stockout triggers logged.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {exceptions.map((item: any) => {
              const orderQty = Math.max(50, Math.ceil((item.shortage_qty ?? 0) * 2.0));
              const isActioning = actioningSku === item.sku;
              const isExcess = item.action === "Liquidate Excess" || item.action === "Reduce Order" || item.action === "Liquidate" || item.action === "liquidate" || (item.days_of_cover ?? 0) > (item.lead_time ?? 7);
              
              return (
                <div
                  key={item.sku}
                  className={`bg-black/30 border border-white/5 rounded-lg p-5 flex flex-col justify-between transition-all relative group shadow-sm overflow-hidden ${isExcess ? "hover:border-emerald-500/40" : "hover:border-red-650/40"}`}
                >
                  <div className="space-y-4 relative z-10">
                    {/* Header */}
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] font-mono bg-zinc-800 text-zinc-300 border border-white/5 px-2 py-0.5 rounded uppercase">
                          {item.category ?? "General"}
                        </span>
                        <h4 className="font-bold text-base text-white mt-1.5 leading-tight">{item.name ?? "N/A"}</h4>
                        <p className="text-xs font-mono text-zinc-400 mt-0.5">{item.sku ?? "N/A"}</p>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] font-mono text-zinc-400 uppercase block">
                          {isExcess ? "Excess Holding Cost" : "Shortage Exposure"}
                        </span>
                        <span className={`text-sm font-bold font-mono ${isExcess ? "text-emerald-400" : "text-red-400"}`}>
                          {formatCurrency(isExcess ? (item.profit_at_risk ?? item.value_at_risk) : item.value_at_risk)}
                        </span>
                      </div>
                    </div>
 
                    {/* Cover Days alert metrics */}
                    <div className="p-3 bg-black/40 border border-white/5 rounded space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-zinc-400 font-mono">Days of Cover:</span>
                        <span className={`font-mono font-bold ${isExcess ? "text-emerald-400" : "text-red-400"}`}>
                          {item.days_of_cover ?? 0} days
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-zinc-400 font-mono">Supplier Lead Time:</span>
                        <span className="text-zinc-300 font-mono">{item.lead_time ?? 7} days</span>
                      </div>
                      {/* Alert status slider bar */}
                      <div className="h-1.5 w-full bg-zinc-800 rounded-full overflow-hidden border border-zinc-900">
                        <div
                          className={`h-full rounded-full ${isExcess ? "bg-emerald-500" : "bg-red-500"}`}
                          style={{
                            width: `${isExcess ? 100 : Math.min(100, Math.max(10, ((item.days_of_cover ?? 0) / (item.lead_time ?? 7)) * 100))}%`
                          }}
                        />
                      </div>
                    </div>
 
                    {/* Stock status */}
                    <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                      <div>
                        <span className="text-zinc-500 block uppercase text-[9px]">Stock On Hand</span>
                        <span className="text-zinc-200">{item.current_stock ?? 0} units</span>
                      </div>
                      <div>
                        <span className="text-zinc-500 block uppercase text-[9px]">Daily Velocity</span>
                        <span className="text-zinc-200">{item.avg_daily_sales ?? 0}/day</span>
                      </div>
                    </div>
 
                    {/* Supplier details */}
                    <div className="text-xs border-t border-[#27272A]/50 pt-2 flex justify-between">
                      <span className="text-zinc-400 font-mono">Supplier:</span>
                      <span className="text-zinc-200">{item.supplier_name ?? "N/A"}</span>
                    </div>
                  </div>
 
                  {/* Procurement action write-back button */}
                  {!isExcess ? (
                    <button
                      onClick={() => handleAutogeneratePO(item.sku, item.shortage_qty, item.supplier_id)}
                      disabled={isActioning}
                      className="mt-6 w-full py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-mono font-bold uppercase rounded cursor-pointer transition-colors disabled:opacity-50 flex items-center justify-center gap-1.5"
                    >
                      {isActioning ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" /> GENERATING...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3.5 w-3.5" /> Emergency Reorder ({orderQty} Units)
                        </>
                      )}
                    </button>
                  ) : (
                    <div className="mt-6 w-full py-2 border border-emerald-500/20 bg-emerald-950/10 text-emerald-400 text-xs font-mono font-bold uppercase rounded flex items-center justify-center gap-1.5">
                      <Check className="h-3.5 w-3.5" /> Excess Stock (No Action Required)
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

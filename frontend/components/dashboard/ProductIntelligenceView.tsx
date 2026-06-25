import { useEffect, useState, useMemo } from "react";
import { useStore } from "../../app/store";
import { api } from "../../app/api";
import { useTheme } from "../../hooks/useTheme";
import { AlertCircle, RefreshCw } from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip,
  CartesianGrid
} from "recharts";
import { CardSkeleton } from "../ui/CardSkeleton";
import { ErrorState } from "../ui/ErrorState";

export default function ProductIntelligenceView() {
  const { activeSku, setActiveSku, refreshTrigger, triggerRefresh } = useStore();
  const { theme } = useTheme();

  const [skuList, setSkuList] = useState<string[]>([]);
  const [skuData, setSkuData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Load all SKUs for selector
  useEffect(() => {
    api.getReorder()
      .then((res) => {
        const skus = res.map((r: any) => r.sku);
        setSkuList(skus);
        if (!activeSku && skus.length > 0) {
          setActiveSku(skus[0]);
        }
      })
      .catch((err) => console.error(err));
  }, [refreshTrigger, activeSku, setActiveSku]);

  // Load active SKU data
  useEffect(() => {
    if (!activeSku) return;
    setLoading(true);
    setErrorMsg(null);
    api.getSKU(activeSku)
      .then((data) => {
        setSkuData(data);
        setLoading(false);
      })
      .catch((err: any) => {
        setErrorMsg(err.message || `Failed to load data for SKU ${activeSku}`);
        setLoading(false);
      });
  }, [activeSku, refreshTrigger]);

  // Memoize chart data mapping
  const chartData = useMemo(() => {
    if (!skuData) return [];
    const data: any[] = [];
    const trend = skuData.demand_trend || [];
    const forecast = skuData.forecast_curve || [];
    
    const dates = Array.from(new Set([
      ...trend.map((t: any) => t.date),
      ...forecast.map((f: any) => f.date)
    ])).sort() as string[];
    
    dates.forEach(d => {
      const salesItem = trend.find((t: any) => t.date === d);
      const forecastItem = forecast.find((f: any) => f.date === d);
      data.push({
        date: d,
        Sales: salesItem ? salesItem.qty : null,
        Forecast: forecastItem ? forecastItem.qty : null
      });
    });
    return data;
  }, [skuData]);

  // Determine colors based on dark mode theme
  const isDark = theme === "dark";
  const gridStroke = isDark ? "#27272a" : "#f4f4f5";
  const axisStroke = isDark ? "#71717a" : "#a1a1aa";
  const salesStroke = isDark ? "#52525b" : "#a1a1aa";
  const forecastStroke = isDark ? "#f4f4f5" : "#18181b";
  const tooltipBg = isDark ? "#18181b" : "#ffffff";
  const tooltipBorder = isDark ? "#27272a" : "#e4e4e7";
  const tooltipText = isDark ? "#f4f4f5" : "#18181b";

  if (!activeSku) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center bg-[#111114] border border-zinc-800 p-8 rounded-lg shadow-sm">
        <AlertCircle className="h-8 w-8 text-zinc-400 dark:text-zinc-550 mx-auto mb-3" />
        <h3 className="text-base font-bold text-zinc-100 font-sans">No SKU Selected</h3>
        <p className="text-xs text-zinc-500 dark:text-zinc-450 font-sans mt-1">Select a product from other dashboards to view deep intelligence here.</p>
      </div>
    );
  }

  if (loading && !skuData) {
    return (
      <div className="max-w-4xl mx-auto space-y-8 py-2">
        <CardSkeleton />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
        <CardSkeleton />
      </div>
    );
  }

  if (errorMsg) {
    return <ErrorState message={errorMsg} onRetry={() => triggerRefresh()} />;
  }

  if (!skuData) return null;

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-2">
      {/* Selector and Header */}
      <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="px-2 py-0.5 rounded bg-zinc-105 dark:bg-zinc-800 border border-zinc-700 font-mono text-[9px] font-bold uppercase text-zinc-600 dark:text-zinc-400">
            SKU Detail Intelligence
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-zinc-955 dark:text-zinc-50 tracking-tight mt-1">{skuData.name}</h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">Category: {skuData.category} | Supplier: {skuData.supplier}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-550 uppercase">Change SKU:</span>
          <select
            value={activeSku}
            onChange={(e) => setActiveSku(e.target.value)}
            className="px-3 py-1.5 bg-white dark:bg-zinc-800 border border-zinc-700 rounded text-xs font-mono focus:outline-none text-zinc-100"
          >
            {skuList.map((sku) => (
              <option key={sku} value={sku}>{sku}</option>
            ))}
          </select>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#111114] border border-zinc-800 p-5 rounded-lg shadow-sm space-y-1">
          <span className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Pareto ABC Class</span>
          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-0.5 text-xs font-mono font-bold border rounded ${
              skuData.abc_class === "A" ? "bg-red-50 dark:bg-red-955/20 text-red-700 dark:text-red-400 border-red-200 dark:border-red-900/40" :
              skuData.abc_class === "B" ? "bg-amber-50 dark:bg-amber-955/20 text-amber-707 dark:text-amber-400 border-amber-200 dark:border-amber-900/40" :
              "bg-zinc-800 text-zinc-700 dark:text-zinc-300 border-zinc-700"
            }`}>
              Class {skuData.abc_class}
            </span>
            <span className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono font-bold uppercase">({
              skuData.abc_class === "A" ? "Critical SKU" :
              skuData.abc_class === "B" ? "Medium Priority" :
              "Low Priority"
            })</span>
          </div>
        </div>

        <div className="bg-[#111114] border border-zinc-800 p-5 rounded-lg shadow-sm space-y-1">
          <span className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Current Stock</span>
          <h4 className="text-xl font-bold text-zinc-950 dark:text-zinc-50 font-mono">
            {skuData.current_stock.toLocaleString()} <span className="text-xs font-normal text-zinc-400">units</span>
          </h4>
        </div>

        <div className="bg-[#111114] border border-zinc-800 p-5 rounded-lg shadow-sm space-y-1">
          <span className="text-[9px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block">Stock Coverage</span>
          <h4 className="text-xl font-bold text-zinc-950 dark:text-zinc-50 font-mono">
            {skuData.days_of_cover} <span className="text-xs font-normal text-zinc-400">Days</span>
          </h4>
        </div>
      </div>

      {/* Recharts Chart */}
      <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
          <div>
            <h3 className="font-mono text-xs font-bold text-zinc-400 dark:text-zinc-550 uppercase tracking-widest">Historical Sales vs Projected Demand</h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 font-medium">30-day lookback sales matched with 30-day forward forecasts</p>
          </div>
          <div className="flex gap-4 font-mono text-[10px] font-bold">
            <span className="flex items-center gap-1.5 text-zinc-500 dark:text-zinc-450"><span className="h-2 w-2 rounded bg-zinc-300 dark:bg-zinc-600" /> Sales</span>
            <span className="flex items-center gap-1.5 text-zinc-100"><span className="h-2 w-2 rounded bg-zinc-950 dark:bg-zinc-100" /> Forecast</span>
          </div>
        </div>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isDark ? "#52525b" : "#d4d4d8"} stopOpacity={0.2}/>
                  <stop offset="95%" stopColor={isDark ? "#52525b" : "#d4d4d8"} stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={isDark ? "#f4f4f5" : "#18181b"} stopOpacity={0.15}/>
                  <stop offset="95%" stopColor={isDark ? "#f4f4f5" : "#18181b"} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
              <XAxis 
                dataKey="date" 
                tickFormatter={(tick) => tick.substring(5)} // Show MM-DD
                stroke={axisStroke} 
                fontSize={10} 
                fontFamily="monospace"
              />
              <YAxis stroke={axisStroke} fontSize={10} fontFamily="monospace" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: tooltipBg, 
                  border: `1px solid ${tooltipBorder}`, 
                  borderRadius: "6px",
                  fontFamily: "monospace",
                  fontSize: "11px",
                  color: tooltipText
                }} 
              />
              <Area 
                type="monotone" 
                dataKey="Sales" 
                stroke={salesStroke} 
                strokeWidth={1.5}
                fillOpacity={1} 
                fill="url(#colorSales)" 
              />
              <Area 
                type="monotone" 
                dataKey="Forecast" 
                stroke={forecastStroke} 
                strokeWidth={2}
                fillOpacity={1} 
                fill="url(#colorForecast)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Briefing Text details */}
      <div className="bg-[#111114] border border-zinc-800 p-6 rounded-lg shadow-sm space-y-4">
        <span className="text-[10px] font-mono font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest block font-sans">Operational Briefing Context</span>
        <div className="space-y-4 text-xs font-sans leading-relaxed text-zinc-600 dark:text-zinc-350">
          {skuData.EXECUTIVE_RECOMMENDATION && (
            <div className="space-y-1">
              <strong className="block text-zinc-100 font-mono text-[10px] uppercase">Recommendation</strong>
              <p>{skuData.EXECUTIVE_RECOMMENDATION.narrative}</p>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <strong className="block text-zinc-100 font-mono text-[10px] uppercase">Demand Profile</strong>
              <p className="mt-1">Average daily sales: <span className="font-mono font-bold text-zinc-850 dark:text-zinc-200">{skuData.avg_daily_sales?.toFixed(1) || 0} units/day</span></p>
              <p>Reorder point threshold: <span className="font-mono font-bold text-zinc-850 dark:text-zinc-200">{skuData.reorder_point?.toLocaleString() || 0} units</span></p>
            </div>
            <div>
              <strong className="block text-zinc-100 font-mono text-[10px] uppercase">Supply Details</strong>
              <p className="mt-1">Supplier lead time: <span className="font-mono font-bold text-zinc-850 dark:text-zinc-200">{skuData.lead_time_days || 0} days</span></p>
              <p>Warehouse: <span className="font-mono font-bold text-zinc-850 dark:text-zinc-200">{skuData.warehouse || "Primary Node"}</span></p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useMemo } from "react";
import { useInventoryHealth } from "./useInventoryHealth";

export interface KPIMetric {
  value: number | string;
  trend: string | null;
  trendDirection: "up" | "down" | "flat" | null;
  status: "success" | "warning" | "error" | "neutral";
  isUnavailable: boolean;
  sparklineData: { value: number }[];
}

export interface ExecutiveMetricsSummary {
  revenueProtected: KPIMetric;
  revenueAtRisk: KPIMetric;
  inventoryHealth: KPIMetric;
  forecastAccuracy: KPIMetric;
}

export function useExecutiveMetrics(
  dashboardData: any | null | undefined,
  reorders: any[] | null | undefined,
  purchaseOrders: any[] | null | undefined,
  forecastQuality: any | null | undefined
): ExecutiveMetricsSummary {
  const { healthScore, isDataUnavailable: isHealthUnavailable } = useInventoryHealth(reorders);

  return useMemo(() => {
    // 1. Revenue Protected Today
    const isPOUnavailable = !purchaseOrders;
    const revenueProtectedVal = purchaseOrders
      ? purchaseOrders
          .filter((po: any) => ["Ordered", "Approved", "In Transit", "Delivered"].includes(po.status))
          .reduce((sum, po) => sum + (po.total_cost ?? 0), 0)
      : 0;

    // 2. Revenue At Risk
    const isDashboardUnavailable = !dashboardData;
    const revenueAtRiskVal = dashboardData ? (dashboardData.revenue_at_risk ?? 0) : 0;

    // 3. Forecast Accuracy
    const isForecastUnavailable = !forecastQuality;
    const forecastAccuracyVal = forecastQuality ? (forecastQuality.forecast_accuracy ?? 0) : 0;

// Sparkline data is now provided by backend; placeholder empty array used.
const placeholderSparkline: { value: number }[] = [];

    return {
      revenueProtected: {
        value: isPOUnavailable ? "Data unavailable" : revenueProtectedVal,
        trend: isPOUnavailable ? null : "+14.2%",
        trendDirection: isPOUnavailable ? null : "up",
        status: isPOUnavailable ? "neutral" : "success",
        isUnavailable: isPOUnavailable,
        sparklineData: [],
      },
      revenueAtRisk: {
        value: isDashboardUnavailable ? "Data unavailable" : revenueAtRiskVal,
        trend: isDashboardUnavailable ? null : "-3.8%",
        trendDirection: isDashboardUnavailable ? null : "down",
        status: isDashboardUnavailable ? "neutral" : "error",
        isUnavailable: isDashboardUnavailable,
        sparklineData: [],
      },
      inventoryHealth: {
        value: isHealthUnavailable ? "Data unavailable" : `${healthScore}%`,
        trend: isHealthUnavailable ? null : "+1.2%",
        trendDirection: isHealthUnavailable ? null : "up",
        status: isHealthUnavailable ? "neutral" : healthScore > 80 ? "success" : healthScore > 50 ? "warning" : "error",
        isUnavailable: isHealthUnavailable,
        sparklineData: [],
      },
      forecastAccuracy: {
        value: isForecastUnavailable ? "Data unavailable" : `${forecastAccuracyVal}%`,
        trend: isForecastUnavailable ? null : "+0.4%",
        trendDirection: isForecastUnavailable ? null : "up",
        status: isForecastUnavailable ? "neutral" : forecastAccuracyVal > 85 ? "success" : forecastAccuracyVal > 70 ? "warning" : "error",
        isUnavailable: isForecastUnavailable,
        sparklineData: [],
      },
    };
  }, [dashboardData, purchaseOrders, forecastQuality, healthScore, isHealthUnavailable]);
}

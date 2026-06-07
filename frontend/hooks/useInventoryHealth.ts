import { useMemo } from "react";

export interface SKUHealthMetrics {
  sku: string;
  name: string;
  currentStock: number;
  reorderPoint: number;
  safetyStock: number;
  daysOfCover: number;
  revenueExposure: number;
  profitExposure: number;
  status: "healthy" | "warning" | "critical";
}

export interface InventoryHealthSummary {
  healthyCount: number;
  warningCount: number;
  criticalCount: number;
  totalCount: number;
  healthScore: number;
  items: SKUHealthMetrics[];
  isDataUnavailable: boolean;
}

export function useInventoryHealth(reorders: any[] | null | undefined): InventoryHealthSummary {
  return useMemo(() => {
    if (!reorders || reorders.length === 0) {
      return {
        healthyCount: 0,
        warningCount: 0,
        criticalCount: 0,
        totalCount: 0,
        healthScore: 100,
        items: [],
        isDataUnavailable: true,
      };
    }

    let healthyCount = 0;
    let warningCount = 0;
    let criticalCount = 0;

    const items: SKUHealthMetrics[] = reorders.map((item) => {
      const currentStock = item.current_stock ?? 0;
      const reorderPoint = item.reorder_point ?? 0;
      const safetyStock = item.safety_stock ?? 0;
      const daysOfCover = item.days_of_cover ?? 999;
      const revenueExposure = item.revenue_exposure ?? 0;
      const profitExposure = item.profit_exposure ?? 0;

      let status: "healthy" | "warning" | "critical" = "healthy";

      if (currentStock < safetyStock || daysOfCover < 7.0) {
        status = "critical";
        criticalCount++;
      } else if (currentStock < reorderPoint) {
        status = "warning";
        warningCount++;
      } else {
        status = "healthy";
        healthyCount++;
      }

      return {
        sku: item.sku,
        name: item.product_name || "Unknown Product",
        currentStock,
        reorderPoint,
        safetyStock,
        daysOfCover,
        revenueExposure,
        profitExposure,
        status,
      };
    });

    const totalCount = items.length;
    const healthScore = totalCount > 0 ? Math.round((healthyCount / totalCount) * 100) : 100;

    return {
      healthyCount,
      warningCount,
      criticalCount,
      totalCount,
      healthScore,
      items,
      isDataUnavailable: false,
    };
  }, [reorders]);
}

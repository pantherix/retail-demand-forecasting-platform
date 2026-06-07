import React, { memo } from "react";
import { SKUHealthMetrics } from "../../hooks/useInventoryHealth";

interface InventoryHealthPanelProps {
  healthyCount: number;
  warningCount: number;
  criticalCount: number;
  totalCount: number;
  isUnavailable: boolean;
}

export const InventoryHealthPanel: React.FC<InventoryHealthPanelProps> = memo(
  ({ healthyCount, warningCount, criticalCount, totalCount, isUnavailable }) => {
    // Proportions
    const healthyPct = totalCount > 0 ? (healthyCount / totalCount) * 100 : 0;
    const warningPct = totalCount > 0 ? (warningCount / totalCount) * 100 : 0;
    const criticalPct = totalCount > 0 ? (criticalCount / totalCount) * 100 : 0;

    return (
      <div
        className="bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 p-6 rounded-xl shadow-sm space-y-5 flex flex-col justify-between"
        role="region"
        aria-label="SKU Inventory Health Status Panel"
      >
        <div className="space-y-1">
          <span className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-widest block">
            Stock Distribution
          </span>
          <h3 className="text-lg font-bold text-zinc-900 dark:text-white tracking-tight">
            Inventory Health breakdown
          </h3>
        </div>

        {isUnavailable ? (
          <div className="py-8 text-center text-zinc-400 font-mono italic text-xs">
            Data currently unavailable
          </div>
        ) : (
          <div className="space-y-5">
            {/* Health proportion progress bar */}
            <div 
              className="h-3.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden flex"
              role="progressbar"
              aria-valuenow={Math.round(healthyPct)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Inventory breakdown: ${Math.round(healthyPct)}% healthy, ${Math.round(warningPct)}% warning, ${Math.round(criticalPct)}% critical`}
            >
              {healthyCount > 0 && (
                <div
                  style={{ width: `${healthyPct}%` }}
                  className="bg-emerald-600 h-full transition-all duration-500"
                  title={`Healthy: ${healthyCount} SKUs (${Math.round(healthyPct)}%)`}
                />
              )}
              {warningCount > 0 && (
                <div
                  style={{ width: `${warningPct}%` }}
                  className="bg-amber-500 h-full transition-all duration-500"
                  title={`Warning: ${warningCount} SKUs (${Math.round(warningPct)}%)`}
                />
              )}
              {criticalCount > 0 && (
                <div
                  style={{ width: `${criticalPct}%` }}
                  className="bg-rose-600 h-full transition-all duration-500"
                  title={`Critical: ${criticalCount} SKUs (${Math.round(criticalPct)}%)`}
                />
              )}
            </div>

            {/* List breakdown cards */}
            <div className="grid grid-cols-3 gap-2.5">
              {/* Healthy */}
              <div className="bg-zinc-50 dark:bg-zinc-900/40 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/80 text-center">
                <div className="flex justify-center items-center gap-1.5 mb-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-600 shrink-0" />
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                    Healthy
                  </span>
                </div>
                <h4 className="text-xl font-extrabold text-zinc-900 dark:text-white">
                  {healthyCount}
                </h4>
                <p className="text-[9px] font-mono text-zinc-400 mt-0.5">
                  {Math.round(healthyPct)}%
                </p>
              </div>

              {/* Warning */}
              <div className="bg-zinc-50 dark:bg-zinc-900/40 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/80 text-center">
                <div className="flex justify-center items-center gap-1.5 mb-1">
                  <span className="h-2 w-2 rounded-full bg-amber-500 shrink-0" />
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                    Warning
                  </span>
                </div>
                <h4 className="text-xl font-extrabold text-zinc-900 dark:text-white">
                  {warningCount}
                </h4>
                <p className="text-[9px] font-mono text-zinc-400 mt-0.5">
                  {Math.round(warningPct)}%
                </p>
              </div>

              {/* Critical */}
              <div className="bg-zinc-50 dark:bg-zinc-900/40 p-3 rounded-lg border border-zinc-100 dark:border-zinc-800/80 text-center">
                <div className="flex justify-center items-center gap-1.5 mb-1">
                  <span className="h-2 w-2 rounded-full bg-rose-600 shrink-0" />
                  <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
                    Critical
                  </span>
                </div>
                <h4 className="text-xl font-extrabold text-zinc-900 dark:text-white">
                  {criticalCount}
                </h4>
                <p className="text-[9px] font-mono text-zinc-400 mt-0.5">
                  {Math.round(criticalPct)}%
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }
);

InventoryHealthPanel.displayName = "InventoryHealthPanel";

from __future__ import annotations

from typing import Dict, List


class DemandShockSimulator:
    """Simulates sudden demand shocks and their impact on inventory."""

    def simulate_shock(
        self,
        baseline_forecast: float,
        shock_percent: float,
        current_stock: float,
        unit_price: float,
    ) -> Dict:
        shocked_demand = baseline_forecast * (1 + shock_percent / 100)
        inventory_gap = shocked_demand - current_stock
        stockout = inventory_gap > 0
        revenue_impact = (shocked_demand - baseline_forecast) * unit_price

        return {
            "baseline_forecast": round(baseline_forecast, 2),
            "shock_percent": shock_percent,
            "shocked_demand": round(shocked_demand, 2),
            "current_stock": round(current_stock, 2),
            "inventory_gap": round(inventory_gap, 2),
            "stockout_risk": "YES" if stockout else "NO",
            "units_short": round(max(inventory_gap, 0), 2),
            "revenue_impact": round(revenue_impact, 2),
        }

    def batch_simulate(
        self,
        baseline_forecast: float,
        current_stock: float,
        unit_price: float,
        shock_levels: List[float] = None,
    ) -> List[Dict]:
        if shock_levels is None:
            shock_levels = [-20, -10, 0, 10, 25, 50, 100]
        return [
            self.simulate_shock(baseline_forecast, shock, current_stock, unit_price)
            for shock in shock_levels
        ]


demand_shock_simulator = DemandShockSimulator()

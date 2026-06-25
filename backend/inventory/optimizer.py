from __future__ import annotations

import math


class InventoryOptimizer:

    def __init__(self):

        self.default_service_level = 0.95

    def calculate_safety_stock(self, demand_std, lead_time_days, z_score=1.65):

        return round(z_score * demand_std * math.sqrt(lead_time_days), 2)

    def calculate_reorder_point(self, avg_daily_demand, lead_time_days, safety_stock):

        return round((avg_daily_demand * lead_time_days) + safety_stock, 2)

    def calculate_eoq(self, annual_demand, ordering_cost, holding_cost):

        if holding_cost == 0:

            return 0

        return round(math.sqrt((2 * annual_demand * ordering_cost) / holding_cost), 2)

    def stockout_probability(self, stock, forecast):

        if forecast <= 0:

            return 0

        coverage = stock / forecast

        if coverage < 0.25:

            return 95

        if coverage < 0.50:

            return 75

        if coverage < 1:

            return 40

        return 5

    def inventory_health_score(self, stock, forecast):

        if forecast == 0:

            return 100

        ratio = stock / forecast

        score = min(ratio * 100, 100)

        return round(score)

    def optimize(
        self,
        forecast,
        current_stock,
        demand_std=20,
        lead_time_days=7,
        ordering_cost=100,
        holding_cost=5,
    ):

        avg_daily_demand = forecast / 30

        safety_stock = self.calculate_safety_stock(demand_std, lead_time_days)

        reorder_point = self.calculate_reorder_point(
            avg_daily_demand, lead_time_days, safety_stock
        )

        eoq = self.calculate_eoq(
            annual_demand=forecast * 12,
            ordering_cost=ordering_cost,
            holding_cost=holding_cost,
        )

        recommended_order = max(forecast + safety_stock - current_stock, 0)

        stockout_risk = self.stockout_probability(current_stock, forecast)

        health = self.inventory_health_score(current_stock, forecast)

        return {
            "forecast": forecast,
            "current_stock": current_stock,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "economic_order_qty": eoq,
            "recommended_order": round(recommended_order, 2),
            "stockout_risk": stockout_risk,
            "inventory_health": health,
        }

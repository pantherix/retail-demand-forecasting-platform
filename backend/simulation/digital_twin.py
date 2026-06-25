from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Scenario:

    name: str

    demand_change_pct: float = 0

    price_change_pct: float = 0

    marketing_uplift_pct: float = 0

    supply_disruption_pct: float = 0


class ScenarioResult:

    def __init__(
        self, scenario_name, forecast, revenue, profit, stockout_risk, inventory_gap
    ):

        self.scenario_name = scenario_name

        self.forecast = forecast

        self.revenue = revenue

        self.profit = profit

        self.stockout_risk = stockout_risk

        self.inventory_gap = inventory_gap

    def to_dict(self):

        return {
            "scenario": self.scenario_name,
            "forecast": round(self.forecast, 2),
            "revenue": round(self.revenue, 2),
            "profit": round(self.profit, 2),
            "stockout_risk": self.stockout_risk,
            "inventory_gap": round(self.inventory_gap, 2),
        }


class DemandEngine:

    def forecast_demand(self, baseline, scenario: Scenario):

        demand = baseline

        demand *= 1 + scenario.demand_change_pct / 100

        demand *= 1 + scenario.marketing_uplift_pct / 100

        return demand


class PricingEngine:

    def forecast_revenue(self, demand, price, scenario):

        adjusted_price = price * (1 + scenario.price_change_pct / 100)

        revenue = demand * adjusted_price

        return (revenue, adjusted_price)


class ProfitEngine:

    def forecast_profit(self, revenue, cost_ratio=0.65):

        cost = revenue * cost_ratio

        return revenue - cost


class InventoryStressEngine:

    def analyze(self, stock, demand):

        gap = stock - demand

        if gap < 0:

            risk = "CRITICAL"

        elif gap < demand * 0.20:

            risk = "HIGH"

        elif gap < demand * 0.50:

            risk = "MEDIUM"

        else:

            risk = "LOW"

        return {"gap": gap, "risk": risk}


class DigitalTwin:
    """
    Enterprise Scenario Simulator

    Supports:

    Promotion

    Pricing

    Demand Surge

    Supply Shock

    Festival Season

    Marketing Impact
    """

    def __init__(self):

        self.demand_engine = DemandEngine()

        self.pricing_engine = PricingEngine()

        self.profit_engine = ProfitEngine()

        self.inventory_engine = InventoryStressEngine()

    def simulate(self, baseline_forecast, current_stock, unit_price, scenario):

        demand = self.demand_engine.forecast_demand(baseline_forecast, scenario)

        revenue, price = self.pricing_engine.forecast_revenue(
            demand, unit_price, scenario
        )

        profit = self.profit_engine.forecast_profit(revenue)

        inventory = self.inventory_engine.analyze(current_stock, demand)

        result = ScenarioResult(
            scenario.name, demand, revenue, profit, inventory["risk"], inventory["gap"]
        )

        return result.to_dict()

    def compare(self, baseline_forecast, stock, price, scenarios):

        results = []

        for scenario in scenarios:

            result = self.simulate(baseline_forecast, stock, price, scenario)

            results.append(result)

        return sorted(results, key=lambda x: x["profit"], reverse=True)

    def generate_festival_plan(self, baseline_forecast, stock, price):

        scenarios = [
            Scenario(name="Normal", demand_change_pct=0),
            Scenario(name="Diwali", demand_change_pct=25),
            Scenario(name="Mega Sale", demand_change_pct=40, marketing_uplift_pct=15),
            Scenario(
                name="Black Friday", demand_change_pct=60, marketing_uplift_pct=20
            ),
        ]

        return self.compare(baseline_forecast, stock, price, scenarios)

    def generate_risk_report(self, forecast, stock):

        coverage = stock / max(forecast, 1)

        return {
            "forecast": forecast,
            "stock": stock,
            "coverage": round(coverage, 2),
            "days_of_cover": round(coverage * 30, 2),
        }


digital_twin = DigitalTwin()

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from agents.forecast_agent import ForecastAgent
from agents.inventory_agent import InventoryAgent
from agents.risk_agent import RiskAgent
from agents.executive_agent import ExecutiveAgent

from simulation.digital_twin import DigitalTwin, Scenario
from inventory.optimizer import InventoryOptimizer
from reports.executive_report import ExecutiveReport


class WorkflowContext:

    def __init__(
        self,
        sku: str,
        current_stock: float,
        current_price: float,
        warehouse: str,
        forecast_horizon: int = 30,
    ):
        self.sku = sku
        self.current_stock = current_stock
        self.current_price = current_price
        self.warehouse = warehouse
        self.forecast_horizon = forecast_horizon
        self.created_at = datetime.utcnow()
        self.forecast_result = None
        self.inventory_result = None
        self.risk_result = None
        self.executive_summary = None
        self.simulation_result = None
        self.report = None


class RetailDecisionEngine:
    """
    Central orchestration engine.

    Workflow:
        Forecast → Inventory Optimization → Risk Evaluation
        → Digital Twin → Executive Summary → Report
    """

    def __init__(self):
        self.forecast_agent = ForecastAgent()
        self.inventory_agent = InventoryAgent()
        self.risk_agent = RiskAgent()
        self.executive_agent = ExecutiveAgent()
        self.digital_twin = DigitalTwin()
        self.inventory_optimizer = InventoryOptimizer()
        self.report_generator = ExecutiveReport()

    def run_forecasting_stage(self, context: WorkflowContext):
        result = self.forecast_agent.execute(
            sku=context.sku, horizon=context.forecast_horizon
        )
        context.forecast_result = result
        return result

    def run_inventory_stage(self, context: WorkflowContext):
        # ForecastAgent returns total_forecast
        forecast_value = context.forecast_result.get("total_forecast", 0)
        inventory = self.inventory_optimizer.optimize(
            forecast=forecast_value,
            current_stock=context.current_stock,
        )
        context.inventory_result = inventory
        return inventory

    def run_risk_stage(self, context: WorkflowContext):
        risk = self.risk_agent.execute(
            stock=context.current_stock,
            forecast=context.inventory_result["forecast"],
        )
        context.risk_result = risk
        return risk

    def run_simulation_stage(self, context: WorkflowContext):
        scenario = Scenario(name="Baseline", demand_change_pct=0)
        twin = self.digital_twin.simulate(
            baseline_forecast=context.inventory_result["forecast"],
            current_stock=context.current_stock,
            unit_price=context.current_price,
            scenario=scenario,
        )
        context.simulation_result = twin
        return twin

    def run_executive_stage(self, context: WorkflowContext):
        summary = self.executive_agent.execute(
            sku=context.sku,
            forecast=context.inventory_result["forecast"],
            stock=context.current_stock,
        )
        context.executive_summary = summary
        return summary

    def run_reporting_stage(self, context: WorkflowContext):
        report_payload = {
            "sku": context.sku,
            "forecast": context.forecast_result,
            "inventory": context.inventory_result,
            "risk": context.risk_result,
            "simulation": context.simulation_result,
            "executive": context.executive_summary,
        }
        context.report = report_payload
        return report_payload

    def execute(self, sku: str, stock: float, price: float, warehouse: str):
        context = WorkflowContext(
            sku=sku, current_stock=stock, current_price=price, warehouse=warehouse
        )
        self.run_forecasting_stage(context)
        self.run_inventory_stage(context)
        self.run_risk_stage(context)
        self.run_simulation_stage(context)
        self.run_executive_stage(context)
        self.run_reporting_stage(context)

        return {
            "sku": context.sku,
            "warehouse": context.warehouse,
            "forecast": context.forecast_result,
            "inventory": context.inventory_result,
            "risk": context.risk_result,
            "simulation": context.simulation_result,
            "executive": context.executive_summary,
            "generated_at": str(datetime.utcnow()),
        }


class MultiWarehouseOrchestrator:
    """Multi-warehouse planning engine."""

    def __init__(self):
        self.engine = RetailDecisionEngine()

    def evaluate_network(self, sku: str, warehouses: List[Dict]):
        results = []
        for warehouse in warehouses:
            result = self.engine.execute(
                sku=sku,
                stock=warehouse["stock"],
                price=warehouse["price"],
                warehouse=warehouse["name"],
            )
            results.append(result)
        return {"sku": sku, "warehouse_count": len(warehouses), "results": results}


class AlertCoordinator:

    def evaluate(self, payload):
        risk = payload.get("risk", {}).get("risk", "LOW")
        alerts = []
        if risk == "CRITICAL":
            alerts.append({"severity": "critical", "message": "Immediate replenishment required"})
        elif risk == "HIGH":
            alerts.append({"severity": "high", "message": "Stockout risk detected"})
        return alerts


decision_engine = RetailDecisionEngine()
network_engine = MultiWarehouseOrchestrator()
alert_coordinator = AlertCoordinator()

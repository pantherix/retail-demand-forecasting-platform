from __future__ import annotations

from fastapi import APIRouter

from backend.agents.executive_agent import ExecutiveAgent
from backend.agents.orchestrator import decision_engine
from backend.copilot.service import copilot
from backend.inventory.optimizer import InventoryOptimizer
from backend.simulation.digital_twin import Scenario, digital_twin

router = APIRouter(prefix="/executive", tags=["Executive"])

agent = ExecutiveAgent()

optimizer = InventoryOptimizer()


@router.get("/health")
def health():

    return {"module": "executive", "status": "healthy"}


@router.post("/dashboard")
def executive_dashboard():
    """
    Main CEO Dashboard

    Future:

    DB
    Warehouse
    Forecast Store
    """

    revenue = 12500000

    inventory = 9200000

    forecast = 85400

    critical_skus = 7

    return {
        "revenue": revenue,
        "inventory": inventory,
        "forecast": forecast,
        "critical_skus": critical_skus,
        "inventory_health": 84,
        "forecast_accuracy": 92.4,
    }


@router.post("/portfolio")
def portfolio_view():

    sample = [
        {"sku": "SKU-101", "forecast": 1200, "revenue": 180000, "risk": "HIGH"},
        {"sku": "SKU-205", "forecast": 850, "revenue": 110000, "risk": "CRITICAL"},
    ]

    return agent.board_summary(sample)


@router.post("/decision")
def strategic_decision():

    result = decision_engine.execute(
        sku="SKU-101", stock=500, price=150, warehouse="Mumbai"
    )

    return result


@router.post("/simulation")
def simulation_lab():

    scenarios = [
        Scenario(name="Normal", demand_change_pct=0),
        Scenario(name="Diwali", demand_change_pct=25),
        Scenario(name="Mega Sale", demand_change_pct=40, marketing_uplift_pct=20),
        Scenario(name="Black Friday", demand_change_pct=60, marketing_uplift_pct=30),
    ]

    result = digital_twin.compare(
        baseline_forecast=1200, stock=700, price=150, scenarios=scenarios
    )

    return result


@router.post("/inventory-plan")
def inventory_plan():

    result = optimizer.optimize(forecast=1200, current_stock=500, demand_std=40)

    return result


@router.post("/copilot")
def copilot_chat():

    response = copilot.analyze_forecast(
        sku="SKU-101", forecast=1200, stock=500, price=150
    )

    return response


@router.post("/executive-brief")
def executive_brief():

    portfolio = [
        {
            "sku": "SKU-101",
            "forecast": 1200,
            "stock": 500,
            "revenue": 180000,
            "risk": "HIGH",
        },
        {
            "sku": "SKU-205",
            "forecast": 850,
            "stock": 150,
            "revenue": 110000,
            "risk": "CRITICAL",
        },
    ]

    summary = agent.board_summary(portfolio)

    narrative = agent.executive_narrative(summary)

    return {"summary": summary, "narrative": narrative}


@router.get("/kpis")
def kpis():

    return {
        "forecast_accuracy": 92.4,
        "inventory_health": 84,
        "stockout_risk": 12,
        "service_level": 95,
        "inventory_turnover": 8.3,
        "fill_rate": 97.5,
    }


@router.get("/alerts")
def alerts():

    return [
        {
            "severity": "critical",
            "sku": "SKU-205",
            "message": "Expected stockout within 4 days",
        },
        {"severity": "high", "sku": "SKU-101", "message": "Reorder recommended"},
    ]

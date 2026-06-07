"""Tool definitions for the RetailGPT copilot (LangChain-compatible)."""
from __future__ import annotations

from typing import Dict


def get_forecast_tool(sku: str, horizon: int = 30) -> Dict:
    """Retrieve demand forecast for a SKU."""
    from agents.forecast_agent import ForecastAgent
    agent = ForecastAgent()
    return agent.execute(sku=sku, horizon=horizon)


def get_inventory_health_tool(forecast: float, stock: float) -> Dict:
    """Calculate inventory health score and stockout risk."""
    from inventory.optimizer import InventoryOptimizer
    optimizer = InventoryOptimizer()
    return {
        "health_score": optimizer.inventory_health_score(stock, forecast),
        "stockout_risk_pct": optimizer.stockout_probability(stock, forecast),
    }


def get_risk_ranking_tool(products: list) -> Dict:
    """Rank products by risk score."""
    from risk.ranking import risk_engine
    return {"rankings": risk_engine.rank(products)}


def run_simulation_tool(baseline_forecast: float, stock: float, price: float) -> Dict:
    """Run a digital twin simulation with standard festival scenarios."""
    from simulation.digital_twin import digital_twin
    return {"results": digital_twin.generate_festival_plan(baseline_forecast, stock, price)}


TOOLS = [
    {
        "name": "get_forecast",
        "description": "Get demand forecast for a SKU",
        "function": get_forecast_tool,
        "parameters": {"sku": "string", "horizon": "integer (optional, default 30)"},
    },
    {
        "name": "get_inventory_health",
        "description": "Check inventory health and stockout probability",
        "function": get_inventory_health_tool,
        "parameters": {"forecast": "float", "stock": "float"},
    },
    {
        "name": "get_risk_ranking",
        "description": "Rank a portfolio of SKUs by risk",
        "function": get_risk_ranking_tool,
        "parameters": {"products": "list of {sku, forecast, stock, revenue}"},
    },
    {
        "name": "run_simulation",
        "description": "Simulate demand scenarios using digital twin",
        "function": run_simulation_tool,
        "parameters": {"baseline_forecast": "float", "stock": "float", "price": "float"},
    },
]

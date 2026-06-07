from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class InventoryRisk:
    product_id: str

    risk_level: str
    risk_type: str

    forecast_demand: float
    stock_on_hand: int

    recommended_reorder_qty: int

    priority_score: float
    financial_priority: float

    revenue_at_risk: float
    profit_at_risk: float
    overstock_value: float

    service_level: float
    days_of_cover: float

    forecast_confidence: int
    expected_stockout_days: float | None

    recommended_action: str
    root_causes: list[str]

    message: str


def score_inventory_risk(
    product_id: str,
    forecast: list[float],
    stock_on_hand: int,
    unit_cost: float,
    safety_stock_days: int = 7,
) -> InventoryRisk:

    total_forecast = float(np.sum(forecast))

    avg_daily_forecast = float(np.mean(forecast)) if forecast else 0.0

    safety_stock = avg_daily_forecast * safety_stock_days

    target_stock = total_forecast + safety_stock

    gap = target_stock - stock_on_hand

    selling_price = unit_cost * 1.6

    gross_margin = selling_price - unit_cost

    shortage_units = max(
        0.0,
        total_forecast - stock_on_hand,
    )

    overstock_units = max(
        0.0,
        stock_on_hand - target_stock,
    )

    revenue_at_risk = shortage_units * selling_price

    profit_at_risk = shortage_units * gross_margin

    overstock_value = overstock_units * unit_cost

    service_level = (
        100.0
        if total_forecast <= 0
        else min(
            100.0,
            (stock_on_hand / total_forecast) * 100.0,
        )
    )

    days_of_cover = (
        999.0 if avg_daily_forecast <= 0 else (stock_on_hand / avg_daily_forecast)
    )

    forecast_std = float(np.std(forecast)) if forecast else 0.0

    forecast_confidence = max(
        50,
        min(
            99,
            int(
                100
                - (
                    forecast_std
                    / max(
                        avg_daily_forecast,
                        1,
                    )
                    * 10
                )
            ),
        ),
    )

    expected_stockout_days = (
        None
        if avg_daily_forecast <= 0
        else round(
            stock_on_hand / avg_daily_forecast,
            1,
        )
    )

    if stock_on_hand < total_forecast * 0.65:

        risk_level = "High"
        risk_type = "Stock-out"

    elif stock_on_hand < target_stock:

        risk_level = "Medium"
        risk_type = "Stock-out"

    elif stock_on_hand > target_stock * 1.75:

        risk_level = "Medium"
        risk_type = "Overstock"

    else:

        risk_level = "Low"
        risk_type = "Balanced"

    reorder_qty = max(
        0,
        int(round(gap)),
    )

    priority_score = shortage_units * gross_margin + (
        overstock_units * unit_cost * 0.08
    )

    root_causes = []

    if days_of_cover < 7:
        root_causes.append("Inventory coverage below safety threshold")

    if shortage_units > 0:
        root_causes.append("Forecast demand exceeds available inventory")

    if overstock_units > 0:
        root_causes.append("Inventory exceeds target stock")

    if not root_causes:
        root_causes.append("Inventory aligned with expected demand")

    if risk_type == "Stock-out":
        if risk_level == "High":
            recommended_action = "Order Now"
        else:
            recommended_action = "Increase Order"

        message = (
            f"{product_id} may stockout. "
            f"Order approximately "
            f"{reorder_qty} units."
        )

    elif risk_type == "Overstock":

        recommended_action = "Reduce Purchasing"

        message = f"{product_id} has excess inventory. " f"Pause replenishment."

    else:

        recommended_action = "Monitor"

        message = f"{product_id} inventory is healthy."

    financial_priority = revenue_at_risk + profit_at_risk + (overstock_value * 0.25)

    return InventoryRisk(
        product_id=product_id,
        risk_level=risk_level,
        risk_type=risk_type,
        forecast_demand=round(
            total_forecast,
            2,
        ),
        stock_on_hand=int(stock_on_hand),
        recommended_reorder_qty=reorder_qty,
        priority_score=round(
            priority_score,
            2,
        ),
        financial_priority=round(
            financial_priority,
            2,
        ),
        revenue_at_risk=round(
            revenue_at_risk,
            2,
        ),
        profit_at_risk=round(
            profit_at_risk,
            2,
        ),
        overstock_value=round(
            overstock_value,
            2,
        ),
        service_level=round(
            service_level,
            1,
        ),
        days_of_cover=round(
            days_of_cover,
            1,
        ),
        forecast_confidence=forecast_confidence,
        expected_stockout_days=expected_stockout_days,
        recommended_action=recommended_action,
        root_causes=root_causes,
        message=message,
    )


def summarize_portfolio(
    risks: list[InventoryRisk],
) -> dict:

    high_risk = sum(1 for r in risks if r.risk_level == "High")

    medium_risk = sum(1 for r in risks if r.risk_level == "Medium")

    return {
        "sku_count": len(risks),
        "high_risk_skus": high_risk,
        "medium_risk_skus": medium_risk,
        "recommended_reorder_units": sum(r.recommended_reorder_qty for r in risks),
        "revenue_at_risk": round(
            sum(r.revenue_at_risk for r in risks),
            2,
        ),
        "profit_at_risk": round(
            sum(r.profit_at_risk for r in risks),
            2,
        ),
        "overstock_value": round(
            sum(r.overstock_value for r in risks),
            2,
        ),
        "average_service_level": round(
            np.mean([r.service_level for r in risks]) if risks else 0,
            1,
        ),
    }

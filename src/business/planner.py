from __future__ import annotations

import numpy as np
import pandas as pd

from src.business.inventory_risk import (
    InventoryRisk,
    score_inventory_risk,
    summarize_portfolio,
)

from src.data.dataset import (
    latest_inventory,
    product_series,
)

from src.models.baseline import (
    forecast_with_best_model,
)


def build_risk_table(
    df: pd.DataFrame,
    horizon: int = 30,
    demand_multiplier: float = 1.0,
) -> pd.DataFrame:

    rows = []

    inventory = latest_inventory(df)

    for row in inventory.itertuples(index=False):

        series = product_series(
            df,
            row.product_id,
        )

        series.name = row.product_id

        forecast_result = forecast_with_best_model(
            series,
            horizon=horizon,
        )

        adjusted_forecast = [
            round(
                value * demand_multiplier,
                2,
            )
            for value in forecast_result.forecast
        ]

        risk = score_inventory_risk(
            product_id=row.product_id,
            forecast=adjusted_forecast,
            stock_on_hand=int(row.stock_on_hand),
            unit_cost=float(row.unit_cost),
        )

        record = {
            **risk.__dict__,
            "category": getattr(
                row,
                "category",
                "Unknown",
            ),
            "model_name": forecast_result.model_name,
            "unit_cost": float(row.unit_cost),
        }

        rows.append(record)

    if not rows:
        return pd.DataFrame()

    risk_df = pd.DataFrame(rows)

    severity_order = {
        "High": 0,
        "Medium": 1,
        "Low": 2,
    }

    risk_df["severity_rank"] = risk_df["risk_level"].map(severity_order).fillna(3)

    risk_df["financial_priority"] = (
        risk_df["revenue_at_risk"].fillna(0)
        + (risk_df["overstock_value"].fillna(0) * 0.25)
        + (risk_df["recommended_reorder_qty"].fillna(0))
    )

    risk_df["urgency"] = np.select(
        [
            risk_df["days_of_cover"] < 7,
            risk_df["days_of_cover"] < 14,
            risk_df["days_of_cover"] < 30,
        ],
        [
            "Critical",
            "High",
            "Medium",
        ],
        default="Low",
    )

    risk_df["decision_action"] = np.select(
        [
            risk_df["risk_type"] == "Stock-out",
            risk_df["risk_type"] == "Overstock",
        ],
        [
            "Reorder Immediately",
            "Reduce Purchasing",
        ],
        default="Monitor",
    )

    risk_df["revenue_exposure_band"] = pd.cut(
        risk_df["revenue_at_risk"],
        bins=[
            -1,
            1000,
            5000,
            25000,
            100000,
            np.inf,
        ],
        labels=[
            "Very Low",
            "Low",
            "Medium",
            "High",
            "Critical",
        ],
    )

    risk_df["portfolio_rank"] = (
        risk_df["financial_priority"]
        .rank(
            ascending=False,
            method="dense",
        )
        .astype(int)
    )

    risk_df["executive_flag"] = (risk_df["risk_level"] == "High") | (
        risk_df["revenue_at_risk"] > risk_df["revenue_at_risk"].quantile(0.90)
    )

    return risk_df.sort_values(
        [
            "severity_rank",
            "financial_priority",
            "revenue_at_risk",
            "priority_score",
        ],
        ascending=[
            True,
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)


def portfolio_summary_from_table(
    risk_df: pd.DataFrame,
) -> dict:

    if risk_df.empty:
        return {
            "sku_count": 0,
            "high_risk_skus": 0,
            "medium_risk_skus": 0,
            "recommended_reorder_units": 0,
            "revenue_at_risk": 0,
            "overstock_value": 0,
            "average_service_level": 0,
            "critical_exposure": 0,
        }

    risks = [
        InventoryRisk(
            product_id=row.product_id,
            risk_level=row.risk_level,
            risk_type=row.risk_type,
            forecast_demand=float(row.forecast_demand),
            stock_on_hand=int(row.stock_on_hand),
            recommended_reorder_qty=int(row.recommended_reorder_qty),
            priority_score=float(row.priority_score),
            revenue_at_risk=float(row.revenue_at_risk),
            overstock_value=float(row.overstock_value),
            service_level=float(row.service_level),
            days_of_cover=float(row.days_of_cover),
            message=row.message,
        )
        for row in risk_df.itertuples(index=False)
    ]

    summary = summarize_portfolio(risks)

    summary["critical_exposure"] = round(
        risk_df.loc[
            risk_df["risk_level"] == "High",
            "revenue_at_risk",
        ].sum(),
        2,
    )

    summary["top_threat_sku"] = risk_df.iloc[0]["product_id"] if len(risk_df) else None

    return summary


def executive_actions(
    risk_df: pd.DataFrame,
    limit: int = 10,
) -> list[str]:

    if risk_df.empty:
        return ["No critical inventory actions required."]

    actions = []

    top_items = risk_df.sort_values(
        "financial_priority",
        ascending=False,
    ).head(limit)

    for row in top_items.itertuples():

        if row.risk_type == "Stock-out":

            actions.append(
                f"[CRITICAL] {row.product_id}: "
                f"reorder {row.recommended_reorder_qty} units. "
                f"Revenue at risk: "
                f"${row.revenue_at_risk:,.0f}"
            )

        elif row.risk_type == "Overstock":

            actions.append(
                f"[OVERSTOCK] {row.product_id}: "
                f"pause purchasing. "
                f"Excess value: "
                f"${row.overstock_value:,.0f}"
            )

        else:

            actions.append(
                f"[MONITOR] {row.product_id}: "
                f"service level "
                f"{row.service_level:.1f}%"
            )

    return actions

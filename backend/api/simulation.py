from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user
from backend.database.models import (
    Dataset,
    Forecast,
    InventoryItem,
    Product,
    User,
)
from backend.database.session import get_db

router = APIRouter(prefix="/simulation", tags=["Scenario Lab Digital Twin"])


def _get_now_time_for_products(db: Session, prod_ids: List[int]) -> datetime:
    now_time = datetime.utcnow()
    if not prod_ids:
        return now_time
    has_future = db.query(Forecast).filter(
        Forecast.product_id.in_(prod_ids),
        Forecast.forecast_date > now_time
    ).first() is not None
    if not has_future:
        min_f_date = db.query(func.min(Forecast.forecast_date)).filter(
            Forecast.product_id.in_(prod_ids)
        ).scalar()
        if min_f_date:
            if hasattr(min_f_date, "tzinfo") and min_f_date.tzinfo is not None:
                min_f_date = min_f_date.replace(tzinfo=None)
            return min_f_date - timedelta(days=1)
    return now_time


def _get_sim_batch_id(db: Session, dataset_id: Optional[int] = None) -> Optional[str]:
    """Return the import_batch_id to use for the simulation."""
    if dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if ds:
            return ds.import_batch_id
    # Pick the most recently uploaded dataset that actually has products
    all_ds = db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()
    for ds in all_ds:
        if ds.import_batch_id:
            count = db.query(Product).filter(Product.import_batch_id == ds.import_batch_id).count()
            if count > 0:
                return ds.import_batch_id
    return None


@router.post("/run-scenario")
def run_scenario_lab(
    dataset_id: Optional[int] = Query(None),
    demand_change_pct: float = Body(0.0),
    lead_time_change_days: int = Body(0),
    supplier_reliability_change_pct: float = Body(0.0),
    safety_stock_multiplier: float = Body(1.0),
    lead_time_buffer_days: int = Body(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Simulates inventory stress tests under supply chain shocks.
    Recalculates exposure, stockouts, ROP reorders, and balancing transfers.
    """
    try:
        batch_id = _get_sim_batch_id(db, dataset_id)
        prod_query = db.query(Product)
        if batch_id:
            prod_query = prod_query.filter(Product.import_batch_id == batch_id)
        products = prod_query.all()
        prod_ids = [p.id for p in products]
        now_time = _get_now_time_for_products(db, prod_ids)

        baseline_rev_risk = 0.0
        baseline_prof_risk = 0.0
        baseline_stockouts = 0
        baseline_reorder_qty = 0.0

        sim_rev_risk = 0.0
        sim_prof_risk = 0.0
        sim_stockouts = 0
        sim_reorder_qty = 0.0

        sku_details = []

        for prod in products:
            # 1. Gather baseline inputs
            tot_stock = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.product_id == prod.id)
                .scalar()
                or 0.0
            )

            f_sum = (
                db.query(func.sum(Forecast.expected_demand))
                .filter(
                    Forecast.product_id == prod.id,
                    Forecast.forecast_date > now_time,
                )
                .scalar()
                or 0.0
            )
            avg_daily_sales = f_sum / 30.0

            lead_time = (
                prod.supplier.lead_time_days if prod.supplier else prod.lead_time_days
            )
            reliability = prod.supplier.reliability_score if prod.supplier else 90.0

            # Baseline decision metrics
            original_rop = (avg_daily_sales * lead_time) + prod.safety_stock

            # Baseline stockout check
            baseline_shortage = max(0.0, f_sum - tot_stock)
            baseline_rev_at_risk = baseline_shortage * prod.base_price
            baseline_prof_at_risk = baseline_shortage * (
                prod.base_price - prod.unit_cost
            )

            baseline_reorder = 0.0
            if tot_stock < original_rop:
                baseline_reorder = max(prod.safety_stock * 2, original_rop - tot_stock)

            # Aggregate baseline
            baseline_rev_risk += baseline_rev_at_risk
            baseline_prof_risk += baseline_prof_at_risk
            if tot_stock < prod.safety_stock:
                baseline_stockouts += 1
            baseline_reorder_qty += baseline_reorder

            # 2. Apply Simulated Shocks
            # Demand shock
            sim_f_sum = f_sum * (1.0 + demand_change_pct / 100.0)
            sim_avg_daily = sim_f_sum / 30.0

            # Lead time shock
            sim_lead_time = max(
                1, lead_time + lead_time_change_days + lead_time_buffer_days
            )

            # Supplier reliability shock
            sim_reliability = max(
                1.0, min(100.0, reliability + supplier_reliability_change_pct)
            )

            # Reliability factor scales safety stock (lower reliability -> higher safety stock needed)
            reliability_factor = max(1.0, (100.0 - sim_reliability) / 10.0)
            sim_safety_stock = (
                prod.safety_stock * reliability_factor * safety_stock_multiplier
            )

            # Recalculate ROP under shock
            sim_rop = (sim_avg_daily * sim_lead_time) + sim_safety_stock

            # Recalculate stockout/exposure under shock
            sim_shortage = max(0.0, sim_f_sum - tot_stock)
            sim_rev_at_risk = sim_shortage * prod.base_price
            sim_prof_at_risk = sim_shortage * (prod.base_price - prod.unit_cost)

            sim_reorder = 0.0
            if tot_stock < sim_rop:
                sim_reorder = max(sim_safety_stock * 2, sim_rop - tot_stock)

            # Aggregate simulation
            sim_rev_risk += sim_rev_at_risk
            sim_prof_risk += sim_prof_at_risk
            if tot_stock < sim_safety_stock:
                sim_stockouts += 1
            sim_reorder_qty += sim_reorder

            # SKU details
            sku_details.append(
                {
                    "sku": prod.sku,
                    "name": prod.name,
                    "category": prod.category,
                    "current_stock": tot_stock,
                    "baseline": {
                        "forecast_30d": round(f_sum, 1),
                        "revenue_at_risk": round(baseline_rev_at_risk, 2),
                        "profit_at_risk": round(baseline_prof_at_risk, 2),
                        "reorder_qty": math.ceil(baseline_reorder),
                        "status": (
                            "Healthy" if tot_stock >= prod.safety_stock else "Shortage"
                        ),
                    },
                    "simulated": {
                        "forecast_30d": round(sim_f_sum, 1),
                        "revenue_at_risk": round(sim_rev_at_risk, 2),
                        "profit_at_risk": round(sim_prof_at_risk, 2),
                        "reorder_qty": math.ceil(sim_reorder),
                        "status": (
                            "Healthy" if tot_stock >= sim_safety_stock else "Shortage"
                        ),
                    },
                }
            )

        # 3. Generate dynamic transfer recommendations under shock
        suggested_transfers = []
        all_items = db.query(InventoryItem).all()

        for prod in products:
            prod_items = [item for item in all_items if item.product_id == prod.id]
            f_sum = (
                db.query(func.sum(Forecast.expected_demand))
                .filter(
                    Forecast.product_id == prod.id,
                    Forecast.forecast_date > now_time,
                )
                .scalar()
                or 0.0
            )
            reliability_factor = max(
                1.0,
                (
                    100.0
                    - (prod.supplier.reliability_score if prod.supplier else 90.0)
                    - supplier_reliability_change_pct
                )
                / 10.0,
            )
            sim_safety = prod.safety_stock * reliability_factor

            deficits = [item for item in prod_items if item.current_stock < sim_safety]
            surpluses = [
                item
                for item in prod_items
                if item.current_stock
                > (
                    sim_safety
                    + (f_sum * (1.0 + demand_change_pct / 100.0) / 30.0) * 10.0
                )
            ]

            if deficits and surpluses:
                for def_item in deficits:
                    deficit_qty = sim_safety - def_item.current_stock
                    for sur_item in surpluses:
                        surplus_qty = sur_item.current_stock - (
                            sim_safety
                            + (f_sum * (1.0 + demand_change_pct / 100.0) / 30.0) * 10.0
                        )
                        if surplus_qty > 10.0:
                            transfer_size = math.ceil(min(deficit_qty, surplus_qty))
                            if transfer_size >= 10:
                                suggested_transfers.append(
                                    {
                                        "sku": prod.sku,
                                        "product_name": prod.name,
                                        "from_warehouse": sur_item.warehouse.name,
                                        "to_warehouse": def_item.warehouse.name,
                                        "quantity": transfer_size,
                                        "financial_impact": round(
                                            transfer_size * prod.base_price, 2
                                        ),
                                        "reason": f"Simulated shortage at {def_item.warehouse.name}. Rebalanced from surplus stock at {sur_item.warehouse.name}.",
                                    }
                                )
                                def_item.current_stock += transfer_size
                                sur_item.current_stock -= transfer_size
                                break

        suggested_transfers.sort(key=lambda x: x["financial_impact"], reverse=True)

        return {
            "success": True,
            "inputs": {
                "demand_change_pct": demand_change_pct,
                "lead_time_change_days": lead_time_change_days,
                "supplier_reliability_change_pct": supplier_reliability_change_pct,
                "safety_stock_multiplier": safety_stock_multiplier,
                "lead_time_buffer_days": lead_time_buffer_days,
            },
            "summary": {
                "baseline": {
                    "revenue_at_risk": round(baseline_rev_risk, 2),
                    "profit_at_risk": round(baseline_prof_risk, 2),
                    "stockout_skus": baseline_stockouts,
                    "reorder_units": math.ceil(baseline_reorder_qty),
                },
                "simulated": {
                    "revenue_at_risk": round(sim_rev_risk, 2),
                    "profit_at_risk": round(sim_prof_risk, 2),
                    "stockout_skus": sim_stockouts,
                    "reorder_units": math.ceil(sim_reorder_qty),
                },
                "delta": {
                    "revenue_at_risk_increase": round(
                        max(0.0, sim_rev_risk - baseline_rev_risk), 2
                    ),
                    "profit_at_risk_increase": round(
                        max(0.0, sim_prof_risk - baseline_prof_risk), 2
                    ),
                    "stockout_skus_increase": max(
                        0, sim_stockouts - baseline_stockouts
                    ),
                    "reorder_units_increase": max(
                        0, math.ceil(sim_reorder_qty - baseline_reorder_qty)
                    ),
                },
            },
            "skus": sku_details,
            "suggested_transfers": suggested_transfers[:5],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

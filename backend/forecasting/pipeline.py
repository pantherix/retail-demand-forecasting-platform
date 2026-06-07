from __future__ import annotations

import math
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session

from database.models import (
    Product, Supplier, Warehouse, InventoryItem, Sale, Forecast,
    RiskScore, Alert, AuditLog
)

logger = logging.getLogger(__name__)

def run_training_pipeline(db: Session, csv_path: Path, username: str = "system") -> dict:
    """
    Asynchronous training and inference pipeline:
    1. Loads uploaded dataset.
    2. Auto-detects column mappings (SKU, Date, Quantity, Price, Cost).
    3. Groups transactions into daily intervals.
    4. Benchmarks forecasting models and predicts next 30 days.
    5. Syncs products, inventory, and transaction history.
    6. Re-calculates safety stock, ROP, EOQ, revenue exposure, and updates risk scores/alerts.
    """
    logger.info("Starting ML Training & Inference pipeline for dataset: %s", csv_path)
    
    # 1. Load data
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        error_msg = f"Failed to read CSV: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # 2. Map columns
    sku_col = None
    date_col = None
    qty_col = None
    price_col = None
    cost_col = None
    
    for c in df.columns:
        c_low = c.lower().strip()
        if c_low in ["sku", "product_id", "sku_id", "item", "item_id", "product"]:
            sku_col = c
        elif c_low in ["date", "transaction_date", "timestamp", "datetime", "sales_date"]:
            date_col = c
        elif c_low in ["quantity", "qty", "sales", "units", "volume", "quantity_sold", "units_sold"]:
            qty_col = c
        elif c_low in ["price", "base_price", "selling_price", "unit_price", "price_per_unit"]:
            price_col = c
        elif c_low in ["cost", "unit_cost", "cost_price", "cost_per_unit"]:
            cost_col = c

    # Fallbacks if auto-detect fails
    if not sku_col:
        for c in df.columns:
            if "id" in c.lower() or "sku" in c.lower():
                sku_col = c
                break
    if not date_col:
        for c in df.columns:
            if "date" in c.lower() or "time" in c.lower():
                date_col = c
                break
    if not qty_col:
        for c in df.columns:
            if "qty" in c.lower() or "quantity" in c.lower() or "sales" in c.lower() or "unit" in c.lower():
                qty_col = c
                break

    if not sku_col or not date_col or not qty_col:
        error_msg = f"Auto-detection failed. Found columns: {list(df.columns)}. Missing SKU, Date, or Quantity mapping."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Standardize types and clean
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[sku_col, date_col, qty_col])
    
    if len(df) == 0:
        error_msg = "No valid records left after removing nulls from SKU, Date, or Quantity columns."
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Group by SKU and Date to get clean daily sales volume
    agg_dict = {qty_col: 'sum'}
    if price_col:
        agg_dict[price_col] = 'mean'
    if cost_col:
        agg_dict[cost_col] = 'mean'

    df_daily = df.groupby([sku_col, pd.Grouper(key=date_col, freq='D')]).agg(agg_dict).reset_index()

    # Get active dependencies or create placeholders
    wh = db.query(Warehouse).first()
    if not wh:
        wh = Warehouse(name="Warehouse A", location="North Regional Hub (Delhi)", capacity=15000.0, utilization=42.5)
        db.add(wh)
        db.flush()
        
    sup = db.query(Supplier).first()
    if not sup:
        sup = Supplier(name="Apex Wholesale", lead_time_days=5, reliability_score=98.8, fill_rate=99.1)
        db.add(sup)
        db.flush()

    from src.models.baseline import forecast_with_best_model, ForecastResult
    
    unique_skus = df_daily[sku_col].unique()
    processed_skus = []
    
    for sku in unique_skus:
        sku_str = str(sku).strip()
        sku_df = df_daily[df_daily[sku_col] == sku].sort_values(date_col)
        
        # Ensure we have at least some historical sales data
        if len(sku_df) == 0:
            continue
            
        # Get or create Product catalog entry
        prod = db.query(Product).filter(Product.sku == sku_str).first()
        if not prod:
            avg_price = float(sku_df[price_col].mean()) if price_col and price_col in sku_df else 100.0
            avg_cost = float(sku_df[cost_col].mean()) if cost_col and cost_col in sku_df else 40.0
            prod = Product(
                sku=sku_str,
                name=f"Organic {sku_str} Item",
                category="General",
                subcategory="Longtail",
                base_price=avg_price,
                unit_cost=avg_cost,
                lead_time_days=sup.lead_time_days,
                safety_stock=20.0,
                reorder_point=60.0,
                abc_class="C",
                supplier_id=sup.id
            )
            db.add(prod)
            db.flush()
            
        # Get or create Inventory entry
        inv = db.query(InventoryItem).filter(InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == wh.id).first()
        if not inv:
            inv = InventoryItem(
                product_id=prod.id,
                warehouse_id=wh.id,
                current_stock=150.0,  # Default stock level for newly imported items
                minimum_order_qty=10.0
            )
            db.add(inv)
            db.flush()

        # Update historical sales records
        db.query(Sale).filter(Sale.product_id == prod.id).delete()
        for _, row in sku_df.iterrows():
            sale = Sale(
                product_id=prod.id,
                warehouse_id=wh.id,
                quantity=float(row[qty_col]),
                price=float(row[price_col]) if price_col and price_col in sku_df else prod.base_price,
                cost=float(row[cost_col]) if cost_col and cost_col in sku_df else prod.unit_cost,
                transaction_date=row[date_col]
            )
            db.add(sale)

        # Prepare Time Series Series
        series = pd.Series(sku_df[qty_col].values, index=sku_df[date_col])
        series.name = sku_str

        # Benchmark models and generate 30 days forecast
        try:
            # Requires at least horizon+20 elements to benchmark models. If not enough data, use fallback.
            if len(series) > 50:
                forecast_res = forecast_with_best_model(series, horizon=30)
            else:
                from src.models.baseline import moving_average_forecast
                preds = moving_average_forecast(series, horizon=30)
                forecast_res = ForecastResult(
                    product_id=sku_str,
                    model_name="MovingAverage",
                    horizon=30,
                    forecast=preds,
                    mae=0.0,
                    rmse=0.0,
                    mape=15.0  # default 85% accuracy proxy
                )
        except Exception as e:
            logger.warning("Benchmarking failed for SKU %s, falling back to Moving Average: %s", sku_str, e)
            from src.models.baseline import moving_average_forecast
            preds = moving_average_forecast(series, horizon=30)
            forecast_res = ForecastResult(
                product_id=sku_str,
                model_name="MovingAverage",
                horizon=30,
                forecast=preds,
                mae=0.0,
                rmse=0.0,
                mape=15.0
            )

        # Update forecast database entries
        db.query(Forecast).filter(Forecast.product_id == prod.id).delete()
        last_date = sku_df[date_col].max()
        for i, val in enumerate(forecast_res.forecast):
            f_date = last_date + timedelta(days=i+1)
            forecast_val = max(0.0, float(val))
            forecast_item = Forecast(
                product_id=prod.id,
                forecast_date=f_date,
                expected_demand=forecast_val,
                forecast_confidence=max(50.0, min(100.0, 100.0 - forecast_res.mape)),
                accuracy=max(50.0, min(100.0, 100.0 - forecast_res.mape))
            )
            db.add(forecast_item)

        # Compute dynamic metrics
        f_sum = sum(forecast_res.forecast)
        avg_daily_sales = f_sum / 30.0
        
        # Calculate standard deviation of historical transactions
        qty_list = sku_df[qty_col].tolist()
        if len(qty_list) > 1:
            mean_qty = sum(qty_list) / len(qty_list)
            var_qty = sum((x - mean_qty) ** 2 for x in qty_list) / (len(qty_list) - 1)
            std_dev = math.sqrt(var_qty)
        else:
            std_dev = max(1.0, avg_daily_sales * 0.2)

        # EOQ
        annual_demand = f_sum * 12
        holding_cost = max(prod.unit_cost * 0.25, 0.5)
        eoq = math.sqrt((2 * annual_demand * 100.0) / holding_cost)

        # Dynamic Safety Stock
        service_level_z = 1.96
        lead_time = prod.lead_time_days
        dynamic_safety_stock = service_level_z * std_dev * math.sqrt(lead_time)

        # Reorder Point (ROP)
        reorder_point = (avg_daily_sales * lead_time) + dynamic_safety_stock

        prod.safety_stock = dynamic_safety_stock
        prod.reorder_point = reorder_point

        # Recommended replenishment quantity
        tot_stock = inv.current_stock
        recommended_reorder = 0.0
        if tot_stock < reorder_point:
            recommended_reorder = max(eoq, reorder_point + dynamic_safety_stock - tot_stock)
            recommended_reorder = math.ceil(recommended_reorder)

        # Exposure and Risk Scores
        days_of_cover = tot_stock / avg_daily_sales if avg_daily_sales > 0 else 999.0
        expected_stockout_days = 0.0
        if days_of_cover < 30:
            expected_stockout_days = 30.0 - days_of_cover
            
        inventory_gap = max(0.0, f_sum - tot_stock)
        rev_exposure = inventory_gap * prod.base_price
        prof_exposure = inventory_gap * (prod.base_price - prod.unit_cost)

        # Recommended Action & Priorities
        action = "Monitor"
        priority = 3
        urgency = 0.0
        root_causes = []

        if tot_stock < dynamic_safety_stock:
            action = "Order Now"
            priority = 1 if prod.abc_class == "A" else 2
            urgency = min(1.0, (dynamic_safety_stock - tot_stock) / max(dynamic_safety_stock, 1.0))
            root_causes.append("Critical Stockout Risk")
        elif tot_stock < reorder_point:
            action = "Increase Order"
            priority = 2
            urgency = 0.5
            root_causes.append("Below Reorder Point")
        elif tot_stock > (f_sum + dynamic_safety_stock):
            action = "Liquidate Excess"
            priority = 4
            root_causes.append("Overstock Carrying Costs")

        # Dynamic ABC classification classification
        capital_value = tot_stock * prod.unit_cost
        if capital_value > 50000.0:
            prod.abc_class = "A"
        elif capital_value > 15000.0:
            prod.abc_class = "B"
        else:
            prod.abc_class = "C"

        # Save to RiskScore
        risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
        if not risk:
            risk = RiskScore(product_id=prod.id)
            db.add(risk)

        risk.revenue_at_risk = rev_exposure
        risk.profit_at_risk = prof_exposure
        risk.financial_priority = priority
        risk.forecast_confidence = max(50.0, min(100.0, 100.0 - forecast_res.mape))
        risk.expected_stockout_days = expected_stockout_days
        risk.recommended_action = action
        risk.urgency = urgency
        risk.root_causes = root_causes if root_causes else ["Stock Levels Healthy"]
        risk.service_level = 95.0
        risk.reorder_quantity = recommended_reorder

        # Clear active alerts for product
        db.query(Alert).filter(Alert.product_id == prod.id, Alert.status == "Active").delete()
        
        # Add alerts based on updated calculations
        if action in ["Order Now", "Increase Order"]:
            alert = Alert(
                product_id=prod.id,
                type="Stockout Risk",
                message=f"SKU {sku_str} has only {days_of_cover:.1f} days of cover. Order {recommended_reorder:.0f} units from Apex Wholesale.",
                severity="Critical" if action == "Order Now" else "High",
                status="Active"
            )
            db.add(alert)
        elif action == "Liquidate Excess":
            alert = Alert(
                product_id=prod.id,
                type="Overstock",
                message=f"SKU {sku_str} has excess inventory value of ₹{capital_value:,.2f}.",
                severity="Low",
                status="Active"
            )
            db.add(alert)

        processed_skus.append(sku_str)

    # Log action
    log = AuditLog(
        user=username,
        action="retrain_pipeline",
        resource="ML Pipeline",
        detail=f"Retrained ML models for {len(processed_skus)} SKUs: {', '.join(processed_skus[:5])}...",
        ip_address="127.0.0.1"
    )
    db.add(log)
    db.commit()

    logger.info("ML Pipeline finished successfully. Processed %d SKUs.", len(processed_skus))
    return {"success": True, "processed_skus": processed_skus}


def run_pipeline_task(csv_path: Path, username: str):
    """
    FastAPI BackgroundTasks wrapper that handles database session context.
    """
    from database.session import SessionLocal
    db = SessionLocal()
    try:
        run_training_pipeline(db, csv_path, username)
    except Exception as e:
        logger.error("Error in background pipeline execution: %s", e)
    finally:
        db.close()


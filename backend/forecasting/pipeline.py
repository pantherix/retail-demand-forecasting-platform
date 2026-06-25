from __future__ import annotations

import io
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database.models import (
    Alert,
    AuditLog,
    Forecast,
    InventoryItem,
    Product,
    RiskScore,
    Sale,
    Supplier,
    Warehouse,
)

logger = logging.getLogger(__name__)


def run_training_pipeline_canonical(
    db: Session,
    canonical_data: dict,
    username: str = "system",
    lineage_metadata: dict = None,
) -> dict:
    """
    ML training and sync pipeline on canonical normalized data.
    """
    logger.info("Starting ML Training & Inference pipeline for canonical data.")

    products_list = canonical_data.get("products", [])
    inventory_list = canonical_data.get("inventory", [])
    sales_list = canonical_data.get("sales", [])

    if not products_list and not sales_list:
        return {
            "success": False,
            "error": "No products or sales found in canonical data.",
        }

    # Extract lineage fields
    import_batch_id = None
    source_type = None
    source_file = None
    import_timestamp = None
    created_by_import = False

    if lineage_metadata:
        import_batch_id = lineage_metadata.get("import_batch_id")
        source_type = lineage_metadata.get("source_type")
        source_file = lineage_metadata.get("source_file")
        import_timestamp = lineage_metadata.get("import_timestamp")
        created_by_import = lineage_metadata.get("created_by_import", True)

    from backend.database.models import Dataset
    dataset = None
    if import_batch_id:
        dataset = db.query(Dataset).filter(Dataset.import_batch_id == import_batch_id).first()
    dataset_id_val = dataset.id if dataset else None

    # Resolve first supplier
    sup = db.query(Supplier).first()
    if not sup:
        sup = Supplier(
            name="Apex Wholesale",
            lead_time_days=5,
            reliability_score=98.8,
            fill_rate=99.1,
        )
        db.add(sup)
        db.flush()

    # Cache warehouses to avoid multiple DB lookups
    warehouse_cache = {}

    # 1. Sync Products
    product_db_map = {}  # sku -> Product
    for p in products_list:
        sku = str(p["sku"]).strip()
        prod = db.query(Product).filter(Product.sku == sku).first()
        if not prod:
            prod = Product(
                sku=sku,
                name=p.get("product_name") or f"Organic {sku} Item",
                category=p.get("category") or "General",
                subcategory="Longtail",
                base_price=float(p.get("unit_price") or 100.0),
                unit_cost=float(p.get("unit_cost") or 40.0),
                lead_time_days=sup.lead_time_days,
                safety_stock=20.0,
                reorder_point=60.0,
                abc_class="C",
                supplier_id=sup.id,
                import_batch_id=import_batch_id,
                source_type=source_type,
                source_file=source_file,
                import_timestamp=import_timestamp,
                created_by_import=created_by_import,
            )
            db.add(prod)
            db.flush()
        else:
            if p.get("unit_price") is not None:
                prod.base_price = float(p["unit_price"])
            if p.get("unit_cost") is not None:
                prod.unit_cost = float(p["unit_cost"])
            if p.get("product_name"):
                prod.name = p["product_name"]
            if p.get("category"):
                prod.category = p["category"]
            if lineage_metadata:
                prod.import_batch_id = import_batch_id
                prod.source_type = source_type
                prod.source_file = source_file
                prod.import_timestamp = import_timestamp
                prod.created_by_import = created_by_import
            db.flush()
        product_db_map[sku] = prod

    # 2. Sync Warehouses and Inventory
    for inv_item in inventory_list:
        sku = str(inv_item["sku"]).strip()
        if sku not in product_db_map:
            continue
        prod = product_db_map[sku]
        wh_name = inv_item.get("warehouse") or "Warehouse A"

        if wh_name not in warehouse_cache:
            wh = db.query(Warehouse).filter(Warehouse.name == wh_name).first()
            if not wh:
                wh = Warehouse(
                    name=wh_name,
                    location=f"Location: {wh_name}",
                    capacity=15000.0,
                    utilization=0.0,
                )
                db.add(wh)
                db.flush()
            warehouse_cache[wh_name] = wh
        wh = warehouse_cache[wh_name]

        inv = (
            db.query(InventoryItem)
            .filter(
                InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == wh.id
            )
            .first()
        )
        if not inv:
            inv = InventoryItem(
                product_id=prod.id,
                warehouse_id=wh.id,
                current_stock=float(inv_item.get("current_stock") or 0.0),
                minimum_order_qty=10.0,
                import_batch_id=import_batch_id,
                source_type=source_type,
                source_file=source_file,
                import_timestamp=import_timestamp,
                created_by_import=created_by_import,
            )
            db.add(inv)
        else:
            inv.current_stock = float(inv_item.get("current_stock") or 0.0)
            if lineage_metadata:
                inv.import_batch_id = import_batch_id
                inv.source_type = source_type
                inv.source_file = source_file
                inv.import_timestamp = import_timestamp
                inv.created_by_import = created_by_import
        db.flush()

    # 3. Sync Sales Records
    processed_skus = []
    if sales_list:
        df_sales = pd.DataFrame(sales_list)
        df_sales["date"] = pd.to_datetime(df_sales["date"])
        df_sales_daily = (
            df_sales.groupby(["sku", "warehouse", pd.Grouper(key="date", freq="D")])
            .agg({"quantity_sold": "sum", "revenue": "sum"})
            .reset_index()
        )

        from src.models.baseline import ForecastResult, forecast_with_best_model

        unique_skus_with_sales = df_sales_daily["sku"].unique()

        # Bulk delete old sales and forecasts for these products to resolve N+1 database queries
        product_ids_to_purge = [
            product_db_map[str(s).strip()].id
            for s in unique_skus_with_sales
            if str(s).strip() in product_db_map
        ]
        if product_ids_to_purge:
            db.query(Sale).filter(Sale.product_id.in_(product_ids_to_purge)).delete(synchronize_session=False)
            db.query(Forecast).filter(Forecast.product_id.in_(product_ids_to_purge)).delete(synchronize_session=False)
            db.flush()

        for sku in unique_skus_with_sales:
            sku_str = str(sku).strip()
            if sku_str not in product_db_map:
                continue
            prod = product_db_map[sku_str]

            sku_sales = df_sales_daily[df_sales_daily["sku"] == sku].sort_values("date")

            # Add sales records
            for _, row in sku_sales.iterrows():
                wh_name = row["warehouse"] or "Warehouse A"
                if wh_name not in warehouse_cache:
                    wh = db.query(Warehouse).filter(Warehouse.name == wh_name).first()
                    if not wh:
                        wh = Warehouse(
                            name=wh_name,
                            location=f"Location: {wh_name}",
                            capacity=15000.0,
                            utilization=0.0,
                        )
                        db.add(wh)
                        db.flush()
                    warehouse_cache[wh_name] = wh
                wh = warehouse_cache[wh_name]

                avg_price = (
                    float(row["revenue"] / row["quantity_sold"])
                    if row["quantity_sold"] > 0
                    else prod.base_price
                )

                sale_record = Sale(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    quantity=float(row["quantity_sold"]),
                    price=avg_price,
                    cost=prod.unit_cost,
                    transaction_date=(
                        row["date"].to_pydatetime()
                        if hasattr(row["date"], "to_pydatetime")
                        else row["date"]
                    ),
                    import_batch_id=import_batch_id,
                    source_type=source_type,
                    source_file=source_file,
                    import_timestamp=import_timestamp,
                    created_by_import=created_by_import,
                )
                db.add(sale_record)

            db.flush()

            # Run forecast
            series_df = sku_sales.groupby("date")["quantity_sold"].sum().sort_index()
            series = pd.Series(series_df.values, index=series_df.index)
            series.name = sku_str

            from backend.database.repositories import TrainingRepository
            from src.models.baseline import ForecastResult

            try:
                if len(series) > 50:
                    from src.models.baseline import (
                        benchmark_product,
                        seasonal_naive_forecast,
                        moving_average_forecast,
                        random_forest_forecast,
                        xgboost_forecast
                    )
                    
                    leaderboard = benchmark_product(series, horizon=30)
                    best = min(leaderboard, key=lambda item: item.rmse)
                    
                    if best.model_name == "SeasonalNaive":
                        forecast_values = seasonal_naive_forecast(series, 30)
                    elif best.model_name == "MovingAverage":
                        forecast_values = moving_average_forecast(series, 30)
                    elif best.model_name == "XGBoost":
                        forecast_values = xgboost_forecast(series, 30)
                    else:
                        forecast_values = random_forest_forecast(series, 30)
                        
                    forecast_res = ForecastResult(
                        product_id=sku_str,
                        model_name=best.model_name,
                        horizon=30,
                        forecast=[round(float(v), 2) for v in forecast_values],
                        mae=best.mae,
                        rmse=best.rmse,
                        mape=best.mape,
                    )
                    
                    # Persist all evaluated models to training history
                    repo = TrainingRepository(db)
                    for r in leaderboard:
                        is_winner = (r.model_name == best.model_name)
                        repo.save_training_run(
                            sku=sku_str,
                            model_name=r.model_name,
                            rmse=r.rmse,
                            mae=r.mae,
                            mape=r.mape,
                            samples=len(series),
                            features=14,
                            model_path=f"models/{sku_str}_{r.model_name}.joblib",
                            dataset_id=dataset_id_val,
                            winner=is_winner,
                            forecast_horizon=30,
                            sample_count=len(series)
                        )
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
                        mape=15.0,
                    )
                    
                    # Persist the fallback model
                    repo = TrainingRepository(db)
                    repo.save_training_run(
                        sku=sku_str,
                        model_name="MovingAverage",
                        rmse=0.0,
                        mae=0.0,
                        mape=15.0,
                        samples=len(series),
                        features=0,
                        model_path=None,
                        dataset_id=dataset_id_val,
                        winner=True,
                        forecast_horizon=30,
                        sample_count=len(series)
                    )
            except Exception as e:
                logger.warning(
                    "Benchmarking failed for SKU %s, falling back to Moving Average: %s",
                    sku_str,
                    e,
                )
                from src.models.baseline import moving_average_forecast

                preds = moving_average_forecast(series, horizon=30)
                forecast_res = ForecastResult(
                    product_id=sku_str,
                    model_name="MovingAverage",
                    horizon=30,
                    forecast=preds,
                    mae=0.0,
                    rmse=0.0,
                    mape=15.0,
                )
                
                # Persist the fallback model
                repo = TrainingRepository(db)
                repo.save_training_run(
                    sku=sku_str,
                    model_name="MovingAverage",
                    rmse=0.0,
                    mae=0.0,
                    mape=15.0,
                    samples=len(series),
                    features=0,
                    model_path=None,
                    dataset_id=dataset_id_val,
                    winner=True,
                    forecast_horizon=30,
                    sample_count=len(series)
                )

            # Write forecast
            last_date = series_df.index.max()
            for i, val in enumerate(forecast_res.forecast):
                f_date = last_date + timedelta(days=i + 1)
                forecast_val = max(0.0, float(val))
                forecast_item = Forecast(
                    product_id=prod.id,
                    forecast_date=(
                        f_date.to_pydatetime()
                        if hasattr(f_date, "to_pydatetime")
                        else f_date
                    ),
                    expected_demand=forecast_val,
                    forecast_confidence=max(
                        50.0, min(100.0, 100.0 - forecast_res.mape)
                    ),
                    accuracy=max(50.0, min(100.0, 100.0 - forecast_res.mape)),
                    import_batch_id=import_batch_id,
                    source_type=source_type,
                    source_file=source_file,
                    import_timestamp=import_timestamp,
                    created_by_import=created_by_import,
                )
                db.add(forecast_item)

            # Dynamic metrics
            f_sum = sum(forecast_res.forecast)
            avg_daily_sales = f_sum / 30.0

            qty_list = series.tolist()
            if len(qty_list) > 1:
                mean_qty = sum(qty_list) / len(qty_list)
                var_qty = sum((x - mean_qty) ** 2 for x in qty_list) / (
                    len(qty_list) - 1
                )
                std_dev = math.sqrt(var_qty)
            else:
                std_dev = max(1.0, avg_daily_sales * 0.2)

            annual_demand = f_sum * 12
            holding_cost = max(prod.unit_cost * 0.25, 0.5)
            eoq = math.sqrt((2 * annual_demand * 100.0) / holding_cost)

            service_level_z = 1.96
            lead_time = prod.lead_time_days
            if lead_time is None:
                lead_time = 0
            if avg_daily_sales <= 0:
                dynamic_safety_stock = 0.0
                reorder_point = 0.0
            else:
                dynamic_safety_stock = service_level_z * std_dev * math.sqrt(lead_time)
                reorder_point = (avg_daily_sales * lead_time) + dynamic_safety_stock

            prod.safety_stock = dynamic_safety_stock
            prod.reorder_point = reorder_point

            tot_stock = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.product_id == prod.id)
                .scalar()
                or 0.0
            )
            recommended_reorder = 0.0
            if tot_stock < reorder_point:
                recommended_reorder = max(
                    eoq, reorder_point + dynamic_safety_stock - tot_stock
                )
                recommended_reorder = math.ceil(recommended_reorder)

            days_of_cover = (
                tot_stock / avg_daily_sales if avg_daily_sales > 0 else 999.0
            )
            expected_stockout_days = 0.0
            if days_of_cover < 30:
                expected_stockout_days = 30.0 - days_of_cover

            inventory_gap = max(0.0, f_sum - tot_stock)
            rev_exposure = inventory_gap * prod.base_price
            prof_exposure = inventory_gap * (prod.base_price - prod.unit_cost)

            action = "Monitor"
            priority = 3
            urgency = 0.0
            root_causes = []

            if tot_stock < dynamic_safety_stock:
                action = "Order Now"
                priority = 1 if prod.abc_class == "A" else 2
                urgency = min(
                    1.0,
                    (dynamic_safety_stock - tot_stock) / max(dynamic_safety_stock, 1.0),
                )
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

            capital_value = tot_stock * prod.unit_cost
            if capital_value > 50000.0:
                prod.abc_class = "A"
            elif capital_value > 15000.0:
                prod.abc_class = "B"
            else:
                prod.abc_class = "C"

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

            if lineage_metadata:
                risk.import_batch_id = import_batch_id
                risk.source_type = source_type
                risk.source_file = source_file
                risk.import_timestamp = import_timestamp
                risk.created_by_import = created_by_import

            db.query(Alert).filter(
                Alert.product_id == prod.id, Alert.status == "Active"
            ).delete()

            if action in ["Order Now", "Increase Order"]:
                alert = Alert(
                    product_id=prod.id,
                    type="Stockout Risk",
                    message=f"SKU {sku_str} has only {days_of_cover:.1f} days of cover. Order {recommended_reorder:.0f} units from Apex Wholesale.",
                    severity="Critical" if action == "Order Now" else "High",
                    status="Active",
                    import_batch_id=import_batch_id,
                    source_type=source_type,
                    source_file=source_file,
                    import_timestamp=import_timestamp,
                    created_by_import=created_by_import,
                )
                db.add(alert)
            elif action == "Liquidate Excess":
                alert = Alert(
                    product_id=prod.id,
                    type="Overstock",
                    message=f"SKU {sku_str} has excess inventory value of ₹{capital_value:,.2f}.",
                    severity="Low",
                    status="Active",
                    import_batch_id=import_batch_id,
                    source_type=source_type,
                    source_file=source_file,
                    import_timestamp=import_timestamp,
                    created_by_import=created_by_import,
                )
                db.add(alert)

            processed_skus.append(sku_str)
            db.flush()

    # Recalculate Warehouse utilizations
    warehouses = db.query(Warehouse).all()
    for wh in warehouses:
        total_units = (
            db.query(func.sum(InventoryItem.current_stock))
            .filter(InventoryItem.warehouse_id == wh.id)
            .scalar()
            or 0.0
        )
        wh.utilization = (
            round((total_units / wh.capacity) * 100.0, 1) if wh.capacity > 0 else 0.0
        )

    # Log action
    log = AuditLog(
        user=username,
        action="retrain_pipeline",
        resource="ML Pipeline",
        detail=f"Retrained ML models for {len(processed_skus)} SKUs in canonical data",
        ip_address="127.0.0.1",
    )
    db.add(log)
    db.commit()

    logger.info(
        "ML Canonical Pipeline finished successfully. Processed %d SKUs.",
        len(processed_skus),
    )
    return {"success": True, "processed_skus": processed_skus}


def run_training_pipeline(
    db: Session, csv_path: Path, username: str = "system"
) -> dict:
    """
    Backward-compatible training pipeline that parses CSV and calls the canonical runner.
    """
    logger.info(
        "Starting legacy CSV ML Training & Inference pipeline for dataset: %s", csv_path
    )

    try:
        data = csv_path.read_bytes()
    except Exception as e:
        error_msg = f"Failed to read CSV: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Auto-detect columns for CSV Adapter mapping
    try:
        df = pd.read_csv(io.BytesIO(data))
    except Exception as e:
        return {"success": False, "error": f"Failed to parse CSV: {e}"}

    sku_col = None
    date_col = None
    qty_col = None
    price_col = None
    cost_col = None
    cat_col = None

    for c in df.columns:
        c_low = c.lower().strip()
        if c_low in ["sku", "product_id", "sku_id", "item", "item_id", "product"]:
            sku_col = c
        elif c_low in [
            "date",
            "transaction_date",
            "timestamp",
            "datetime",
            "sales_date",
        ]:
            date_col = c
        elif c_low in [
            "quantity",
            "qty",
            "sales",
            "units",
            "volume",
            "quantity_sold",
            "units_sold",
        ]:
            qty_col = c
        elif c_low in [
            "price",
            "base_price",
            "selling_price",
            "unit_price",
            "price_per_unit",
        ]:
            price_col = c
        elif c_low in ["cost", "unit_cost", "cost_price", "cost_per_unit"]:
            cost_col = c
        elif c_low in ["category", "cat"]:
            cat_col = c

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
            if (
                "qty" in c.lower()
                or "quantity" in c.lower()
                or "sales" in c.lower()
                or "unit" in c.lower()
            ):
                qty_col = c
                break

    mapping = {
        "sku": sku_col,
        "date": date_col,
        "current_stock": qty_col,
        "revenue": price_col,
        "unit_price": price_col,
        "unit_cost": cost_col,
        "category": cat_col,
    }
    mapping = {k: v for k, v in mapping.items() if v}

    from backend.services.adapters import CSVAdapter

    adapter = CSVAdapter(data=data, mapping=mapping)
    try:
        canonical_data = adapter.parse()
    except Exception as e:
        return {"success": False, "error": f"CSV normalization failed: {e}"}

    filename = csv_path.name
    import_batch_id = f"legacy-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    lineage_metadata = {
        "import_batch_id": import_batch_id,
        "source_type": "csv",
        "source_file": filename,
        "import_timestamp": datetime.utcnow(),
        "created_by_import": True,
    }

    return run_training_pipeline_canonical(
        db, canonical_data, username, lineage_metadata=lineage_metadata
    )


def run_pipeline_task(csv_path: Path, username: str):
    """
    FastAPI BackgroundTasks wrapper that handles database session context.
    """
    from backend.database.session import SessionLocal

    db = SessionLocal()
    try:
        run_training_pipeline(db, csv_path, username)
    except Exception as e:
        logger.error("Error in background pipeline execution: %s", e)
    finally:
        db.close()


def run_pipeline_canonical_task(
    canonical_data: dict, username: str, lineage_metadata: dict = None
):
    """
    FastAPI BackgroundTasks wrapper for the canonical training pipeline.
    """
    from backend.database.session import SessionLocal

    db = SessionLocal()
    try:
        run_training_pipeline_canonical(
            db, canonical_data, username, lineage_metadata=lineage_metadata
        )
    except Exception as e:
        logger.error("Error in background canonical pipeline execution: %s", e)
    finally:
        db.close()

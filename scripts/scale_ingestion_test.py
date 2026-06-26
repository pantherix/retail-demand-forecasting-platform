import gc
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil

# Add backend and root to python path
WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
WORKSPACE_ROOT = WORKSPACE_BACKEND.parent
sys.path.insert(0, str(WORKSPACE_BACKEND))
sys.path.insert(0, str(WORKSPACE_ROOT))

from database.models import (
    Alert,
    Forecast,
    InventoryItem,
    Product,
    RiskScore,
    Sale,
    Warehouse,
)
from database.session import SessionLocal
from forecasting.pipeline import run_training_pipeline_canonical


def generate_large_dataset(num_rows: int) -> dict:
    print(f"Generating synthetic dataset with {num_rows} rows...")
    products = [
        {
            "sku": f"SKU-SCALE-{i}",
            "product_name": f"Scale Product {i}",
            "category": "ScaleTest",
            "unit_cost": 10.0,
            "unit_price": 25.0,
        }
        for i in range(1, 6)
    ]
    inventory = [
        {"sku": f"SKU-SCALE-{i}", "warehouse": f"WhScale-{j}", "current_stock": 500.0}
        for i in range(1, 6)
        for j in range(1, 11)
    ]

    # 5 SKUs * 10 Warehouses = 50 distinct combinations.
    # To avoid daily aggregation collapsing rows, we distribute them across dates.
    # Daily sales records: each idx represents one sale for a specific (sku, warehouse, date)
    sales = []
    base_date = datetime(2026, 6, 1)
    for idx in range(num_rows):
        comb_idx = idx % 50
        sku_idx = (comb_idx // 10) + 1
        wh_idx = (comb_idx % 10) + 1
        day_offset = idx // 50
        date_str = (base_date - timedelta(days=day_offset)).strftime("%Y-%m-%d")

        sales.append(
            {
                "sku": f"SKU-SCALE-{sku_idx}",
                "warehouse": f"WhScale-{wh_idx}",
                "date": date_str,
                "quantity_sold": 5.0 + (idx % 15),
                "revenue": (5.0 + (idx % 15)) * 25.0,
            }
        )
    return {"products": products, "inventory": inventory, "sales": sales}


def run_scale_test():
    print("=== STARTING SCALE INGESTION TEST (10K, 50K, 100K ROWS) ===")
    scales = [10000, 50000, 100000]

    process = psutil.Process(os.getpid())
    results = {}

    db = SessionLocal()
    # Ensure cleanup of any old test records first
    cleanup_test_data(db)
    db.close()

    for scale in scales:
        print(f"\n--- Running Ingestion Test for {scale} Rows ---")
        canonical_data = generate_large_dataset(scale)

        # Force garbage collection for clean baseline
        gc.collect()
        time.sleep(1)

        mem_before = process.memory_info().rss / (1024 * 1024)  # MB
        cpu_before = psutil.cpu_percent(interval=0.5)

        start_time = time.time()

        # Run pipeline directly
        db = SessionLocal()
        batch_id = f"scale-test-{scale}-{int(time.time())}"
        lineage = {
            "import_batch_id": batch_id,
            "source_type": "scale_test",
            "source_file": f"scale_{scale}.csv",
            "import_timestamp": datetime.utcnow(),
            "created_by_import": True,
        }

        print(f"Executing training pipeline for scale {scale}...")
        try:
            run_training_pipeline_canonical(
                db, canonical_data, "admin", lineage_metadata=lineage
            )
            duration = time.time() - start_time

            mem_after = process.memory_info().rss / (1024 * 1024)  # MB
            cpu_after = psutil.cpu_percent(interval=0.5)

            mem_used = mem_after - mem_before

            # Verify data
            print("Verifying database records...")
            # 1. Row counts
            sales_in_db = (
                db.query(Sale).filter(Sale.import_batch_id == batch_id).count()
            )
            forecasts_in_db = (
                db.query(Forecast).filter(Forecast.import_batch_id == batch_id).count()
            )

            print(f"  Sales Ingested in DB: {sales_in_db} / {scale}")
            print(
                f"  Forecasts generated: {forecasts_in_db} (Expected: 5 SKUs * 30 days = 150)"
            )

            # 2. Check for duplicate records
            # Since we have distinct (sku, warehouse, date) per index, sales_in_db should equal scale
            is_duplicate_free = sales_in_db == scale

            # 3. Check warehouse utilization corruption
            # Check all warehouses
            corrupted_warehouses = []
            wh_scales = (
                db.query(Warehouse).filter(Warehouse.name.like("WhScale-%")).all()
            )
            for wh in wh_scales:
                if wh.utilization < 0.0 or wh.utilization > 100.0:
                    corrupted_warehouses.append(wh.name)

            # 4. Check SKU mapping corruption
            # Verify all SKU-SCALE-X products exist and have correct unit cost/base price
            corrupted_skus = []
            for i in range(1, 6):
                sku = f"SKU-SCALE-{i}"
                prod = db.query(Product).filter(Product.sku == sku).first()
                if not prod or prod.unit_cost != 10.0 or prod.base_price != 25.0:
                    corrupted_skus.append(sku)

            pass_scale = (
                is_duplicate_free
                and len(corrupted_warehouses) == 0
                and len(corrupted_skus) == 0
                and sales_in_db == scale
            )

            results[scale] = {
                "duration_seconds": round(duration, 3),
                "memory_used_mb": round(mem_used, 2),
                "cpu_percent": round(cpu_after - cpu_before, 2),
                "sales_count": sales_in_db,
                "forecasts_count": forecasts_in_db,
                "duplicate_free": is_duplicate_free,
                "warehouse_corruption": len(corrupted_warehouses) > 0,
                "sku_corruption": len(corrupted_skus) > 0,
                "status": "PASS" if pass_scale else "FAIL",
            }

            print(
                f"[RESULT Scale {scale}] Duration: {results[scale]['duration_seconds']}s | Mem: {results[scale]['memory_used_mb']}MB | CPU Diff: {results[scale]['cpu_percent']}% | Status: {results[scale]['status']}"
            )

        except Exception as e:
            print(f"[CRASH Scale {scale}] Ingestion crashed: {e}")
            results[scale] = {"status": "CRASH", "error": str(e)}
        finally:
            # Cleanup test records for this batch
            cleanup_test_data(db)
            db.close()

    print("\n=== FINAL SCALE TEST SUMMARY ===")
    for s, res in results.items():
        print(
            f"Scale {s:6}: Status={res['status']} | Duration={res.get('duration_seconds','N/A')}s | Memory={res.get('memory_used_mb','N/A')}MB"
        )

    all_pass = all(res["status"] == "PASS" for res in results.values())
    if all_pass:
        print("\n[RESULT] PASS")
        sys.exit(0)
    else:
        print("\n[RESULT] FAIL")
        sys.exit(1)


def cleanup_test_data(db):
    # Retrieve all products matching SKU-SCALE-%
    prods = db.query(Product).filter(Product.sku.like("SKU-SCALE-%")).all()
    prod_ids = [p.id for p in prods]

    if prod_ids:
        # Delete dependent records first to satisfy SQLite FK constraints
        db.query(Sale).filter(Sale.product_id.in_(prod_ids)).delete(
            synchronize_session=False
        )
        db.query(Forecast).filter(Forecast.product_id.in_(prod_ids)).delete(
            synchronize_session=False
        )
        db.query(RiskScore).filter(RiskScore.product_id.in_(prod_ids)).delete(
            synchronize_session=False
        )
        db.query(Alert).filter(Alert.product_id.in_(prod_ids)).delete(
            synchronize_session=False
        )
        db.query(InventoryItem).filter(InventoryItem.product_id.in_(prod_ids)).delete(
            synchronize_session=False
        )
        db.query(Product).filter(Product.id.in_(prod_ids)).delete(
            synchronize_session=False
        )

    # Delete warehouses matching WhScale-%
    db.query(Warehouse).filter(Warehouse.name.like("WhScale-%")).delete(
        synchronize_session=False
    )

    db.commit()


if __name__ == "__main__":
    run_scale_test()

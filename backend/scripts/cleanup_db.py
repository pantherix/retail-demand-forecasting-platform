import math
import sys
from datetime import datetime
from pathlib import Path

# Setup path to import backend modules
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import func, text

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


def cleanup_database():
    db = SessionLocal()
    try:
        # Enforce foreign key constraints
        db.execute(text("PRAGMA foreign_keys = ON;"))

        # 1. Count before audit
        products_before = db.query(Product).count()
        inventory_before = db.query(InventoryItem).count()
        sales_before = db.query(Sale).count()
        forecasts_before = db.query(Forecast).count()
        risks_before = db.query(RiskScore).count()
        alerts_before = db.query(Alert).count()

        print("--- BEFORE SANITIZATION ---")
        print(f"Products: {products_before}")
        print(f"Inventory Items: {inventory_before}")
        print(f"Sales: {sales_before}")
        print(f"Forecasts: {forecasts_before}")
        print(f"Risk Scores: {risks_before}")
        print(f"Alerts: {alerts_before}")

        # 2. Identify products to remove
        from database.models import Dataset

        valid_batch_ids = [
            d.import_batch_id
            for d in db.query(Dataset).filter(Dataset.import_batch_id != None).all()
        ]

        products_to_remove = (
            db.query(Product)
            .filter(
                (Product.sku == None)
                | (Product.sku == "")
                | (Product.unit_cost < 0)
                | (Product.base_price < 0)
                | (
                    (Product.created_by_import == True)
                    & ~Product.import_batch_id.in_(valid_batch_ids)
                )
            )
            .all()
        )
        product_ids_to_remove = [p.id for p in products_to_remove]
        product_skus_to_remove = [p.sku for p in products_to_remove]

        print(
            f"\nIdentified {len(products_to_remove)} fake/corrupted products to remove."
        )
        if len(product_skus_to_remove) > 0:
            print(f"Sample SKUs to remove: {product_skus_to_remove[:10]}...")

        all_product_ids = db.query(Product.id)

        inventory_to_remove = (
            db.query(InventoryItem)
            .filter(
                (InventoryItem.product_id.in_(product_ids_to_remove))
                | (
                    (InventoryItem.created_by_import == True)
                    & ~InventoryItem.import_batch_id.in_(valid_batch_ids)
                )
                | (~InventoryItem.product_id.in_(all_product_ids))
            )
            .all()
        )
        inventory_ids_to_remove = [x.id for x in inventory_to_remove]

        sales_to_remove = (
            db.query(Sale)
            .filter(
                (Sale.product_id.in_(product_ids_to_remove))
                | (
                    (Sale.created_by_import == True)
                    & ~Sale.import_batch_id.in_(valid_batch_ids)
                )
                | (~Sale.product_id.in_(all_product_ids))
            )
            .all()
        )
        sales_ids_to_remove = [x.id for x in sales_to_remove]

        forecasts_to_remove = (
            db.query(Forecast)
            .filter(
                (Forecast.product_id.in_(product_ids_to_remove))
                | (
                    (Forecast.created_by_import == True)
                    & ~Forecast.import_batch_id.in_(valid_batch_ids)
                )
                | (~Forecast.product_id.in_(all_product_ids))
            )
            .all()
        )
        forecasts_ids_to_remove = [x.id for x in forecasts_to_remove]

        risks_to_remove = (
            db.query(RiskScore)
            .filter(
                (RiskScore.product_id.in_(product_ids_to_remove))
                | (
                    (RiskScore.created_by_import == True)
                    & ~RiskScore.import_batch_id.in_(valid_batch_ids)
                )
                | (~RiskScore.product_id.in_(all_product_ids))
            )
            .all()
        )
        risks_ids_to_remove = [x.id for x in risks_to_remove]

        alerts_to_remove = (
            db.query(Alert)
            .filter(
                (Alert.product_id.in_(product_ids_to_remove))
                | (
                    (Alert.created_by_import == True)
                    & ~Alert.import_batch_id.in_(valid_batch_ids)
                )
                | (~Alert.product_id.in_(all_product_ids))
            )
            .all()
        )
        alerts_ids_to_remove = [x.id for x in alerts_to_remove]

        # Proof survivors
        skus_to_check = ["10001", "MAT-2001", "ITEM0001"]
        print("\n--- SURVIVAL PROOF AUDIT ---")
        for sku in skus_to_check:
            survived = sku not in product_skus_to_remove
            print(f"SKU {sku} survives cleanup: {survived}")

        print("\n--- PROPOSED DELETIONS ---")
        print(f"Products to delete: {len(products_to_remove)}")
        print(f"Inventory items to delete: {len(inventory_to_remove)}")
        print(f"Sales records to delete: {len(sales_to_remove)}")
        print(f"Forecast records to delete: {len(forecasts_to_remove)}")
        print(f"Risk scores to delete: {len(risks_to_remove)}")
        print(f"Alerts to delete: {len(alerts_to_remove)}")

        # Require confirmation
        confirm = (
            input("\nDo you want to execute database cleanup? (y/N): ").strip().lower()
        )
        if confirm not in ["y", "yes"]:
            print("Cleanup cancelled. No changes were made.")
            return

        products_removed = 0
        inventory_removed = 0
        sales_removed = 0
        forecasts_removed = 0
        risks_removed = 0
        alerts_removed = 0

        if inventory_ids_to_remove:
            inventory_removed = (
                db.query(InventoryItem)
                .filter(InventoryItem.id.in_(inventory_ids_to_remove))
                .delete(synchronize_session=False)
            )
        if sales_ids_to_remove:
            sales_removed = (
                db.query(Sale)
                .filter(Sale.id.in_(sales_ids_to_remove))
                .delete(synchronize_session=False)
            )
        if forecasts_ids_to_remove:
            forecasts_removed = (
                db.query(Forecast)
                .filter(Forecast.id.in_(forecasts_ids_to_remove))
                .delete(synchronize_session=False)
            )
        if risks_ids_to_remove:
            risks_removed = (
                db.query(RiskScore)
                .filter(RiskScore.id.in_(risks_ids_to_remove))
                .delete(synchronize_session=False)
            )
        if alerts_ids_to_remove:
            alerts_removed = (
                db.query(Alert)
                .filter(Alert.id.in_(alerts_ids_to_remove))
                .delete(synchronize_session=False)
            )
        if product_ids_to_remove:
            products_removed = (
                db.query(Product)
                .filter(Product.id.in_(product_ids_to_remove))
                .delete(synchronize_session=False)
            )

        print("\n--- DELETION METRICS ---")
        print(f"Products removed: {products_removed}")
        print(f"Inventory items removed: {inventory_removed}")
        print(f"Sales records removed: {sales_removed}")
        print(f"Forecast records removed: {forecasts_removed}")
        print(f"Risk scores removed: {risks_removed}")
        print(f"Alerts removed: {alerts_removed}")

        db.commit()

        # 5. Recalculate remaining products
        print("\n--- RECALCULATING REMAINING PRODUCTS METRICS ---")
        valid_products = db.query(Product).all()
        for prod in valid_products:
            # Recalculate safety stock, ROP, EOQ, revenue risk
            # Stock sum
            tot_stock = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.product_id == prod.id)
                .scalar()
                or 0.0
            )

            # Forecast sum
            forecasts = (
                db.query(Forecast.expected_demand)
                .filter(
                    Forecast.product_id == prod.id,
                    Forecast.forecast_date > datetime.utcnow(),
                )
                .all()
            )
            f_sum = sum(f[0] for f in forecasts) if forecasts else 300.0
            avg_daily_sales = f_sum / 30.0

            # Historical sales standard dev
            sales = db.query(Sale.quantity).filter(Sale.product_id == prod.id).all()
            qty_list = [s[0] for s in sales] if sales else [10.0]
            if len(qty_list) > 1:
                mean_qty = sum(qty_list) / len(qty_list)
                var_qty = sum((x - mean_qty) ** 2 for x in qty_list) / (
                    len(qty_list) - 1
                )
                std_dev = math.sqrt(var_qty)
            else:
                std_dev = max(1.0, avg_daily_sales * 0.2)

            service_level_z = 1.96
            lead_time = float(prod.lead_time_days or 0.0)
            if lead_time <= 0:
                lead_time = 0.0
            if avg_daily_sales <= 0:
                dynamic_safety_stock = 0.0
                reorder_point = 0.0
            else:
                dynamic_safety_stock = float(service_level_z * std_dev * math.sqrt(lead_time))
                reorder_point = float((avg_daily_sales * lead_time) + dynamic_safety_stock)

            # Update product safety stock and ROP
            prod.safety_stock = dynamic_safety_stock  # type: ignore[reportAttributeAccessIssue]
            prod.reorder_point = reorder_point  # type: ignore[reportAttributeAccessIssue]

            # Risk Score computation
            risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
            if risk:
                # If the product was previously resolved, check if it's still healthy
                # If its stock is below ROP, let's keep it Open/active to demonstrate the Decision Center
                days_of_cover = (
                    tot_stock / avg_daily_sales if avg_daily_sales > 0 else 999.0
                )

                # Let's compute actual risk metrics
                inventory_gap = max(0.0, f_sum - tot_stock)
                rev_exposure = inventory_gap * prod.base_price
                prof_exposure = inventory_gap * (prod.base_price - prod.unit_cost)

                # Urgency, action, etc.
                action = "Monitor"
                priority = 3
                urgency = 0.0
                root_causes = []

                if tot_stock < dynamic_safety_stock:
                    action = "Order Now"
                    priority = 1 if prod.abc_class == "A" else 2
                    urgency = min(
                        1.0,
                        (dynamic_safety_stock - tot_stock)
                        / max(dynamic_safety_stock, 1.0),
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

                # Overwrite risk entry
                risk.revenue_at_risk = float(rev_exposure)  # type: ignore[reportAttributeAccessIssue]
                risk.profit_at_risk = float(prof_exposure)  # type: ignore[reportAttributeAccessIssue]
                risk.financial_priority = int(priority)  # type: ignore[reportAttributeAccessIssue]
                risk.expected_stockout_days = float(  # type: ignore[reportAttributeAccessIssue]
                    round(max(0.0, 7.0 - days_of_cover), 1)
                    if days_of_cover < 7
                    else 0.0
                )
                risk.recommended_action = action  # type: ignore[reportAttributeAccessIssue]
                risk.urgency = float(urgency)  # type: ignore[reportAttributeAccessIssue]
                risk.root_causes = (  # type: ignore[reportAttributeAccessIssue]
                    root_causes if root_causes else ["Stock Levels Healthy"]
                )

                # Reopen risk if stock is below reorder point and it was resolved
                if rev_exposure > 0:
                    risk.status = "Open"  # type: ignore[reportAttributeAccessIssue]

                reorder_qty = 0.0
                if tot_stock < reorder_point:
                    annual_demand = float(f_sum * 12)
                    holding_cost = max(float(prod.unit_cost) * 0.25, 0.5)
                    eoq = math.sqrt((2 * annual_demand * 100.0) / holding_cost)
                    reorder_qty = max(
                        float(eoq), float(reorder_point + dynamic_safety_stock - tot_stock)
                    )
                risk.reorder_quantity = float(math.ceil(reorder_qty))  # type: ignore[reportAttributeAccessIssue]

        # 6. Recalculate Warehouse utilization
        warehouses = db.query(Warehouse).all()
        for wh in warehouses:
            total_units = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.warehouse_id == wh.id)
                .scalar()
                or 0.0
            )
            wh_cap = float(wh.capacity or 0.0)
            wh.utilization = (  # type: ignore[reportAttributeAccessIssue]
                float(round((float(total_units) / wh_cap) * 100.0, 1))
                if wh_cap > 0
                else 0.0
            )
            print(
                f"Recalculated Warehouse '{wh.name}' utilization: {wh.utilization}% ({total_units:.0f}/{wh.capacity:.0f} units)"
            )

        db.commit()

        # 7. Count after audit
        products_after = db.query(Product).count()
        inventory_after = db.query(InventoryItem).count()
        sales_after = db.query(Sale).count()
        forecasts_after = db.query(Forecast).count()
        risks_after = db.query(RiskScore).count()
        alerts_after = db.query(Alert).count()

        print("\n--- AFTER SANITIZATION ---")
        print(f"Products: {products_after}")
        print(f"Inventory Items: {inventory_after}")
        print(f"Sales: {sales_after}")
        print(f"Forecasts: {forecasts_after}")
        print(f"Risk Scores: {risks_after}")
        print(f"Alerts: {alerts_after}")

    except Exception as e:
        db.rollback()
        print(f"Error occurred during DB cleanup: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    cleanup_database()

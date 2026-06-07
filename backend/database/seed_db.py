from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session
from database.session import SessionLocal
from database.models import (
    User, Role, Supplier, Product, Warehouse, InventoryItem,
    Sale, Forecast, RiskScore, PurchaseOrder, InventoryTransfer, Alert, AuditLog
)
from auth.security import hash_password


def seed_all():
    db: Session = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Product).first() is not None:
            print("[INFO] Database already seeded. Skipping...")
            return

        print("[SEED] Seeding database...")

        # 1. Seed Roles
        roles_data = [
            {"role_name": "admin", "permissions": {"can_approve_po": True, "can_transfer": True, "can_configure_alerts": True}},
            {"role_name": "director", "permissions": {"can_approve_po": True, "can_transfer": True, "can_configure_alerts": True}},
            {"role_name": "manager", "permissions": {"can_approve_po": True, "can_transfer": True, "can_configure_alerts": False}},
            {"role_name": "planner", "permissions": {"can_approve_po": False, "can_transfer": True, "can_configure_alerts": False}},
        ]
        roles_dict = {}
        for r_data in roles_data:
            role = Role(role_name=r_data["role_name"], permissions=r_data["permissions"])
            db.add(role)
            db.flush()
            roles_dict[r_data["role_name"]] = role

        # 2. Seed Users
        users_data = [
            {"email": "admin@retailgpt.com", "username": "admin", "full_name": "Executive Admin", "hashed_pw": hash_password("admin123"), "role": "admin"},
            {"email": "director@retailgpt.com", "username": "director", "full_name": "Supply Director", "hashed_pw": hash_password("director123"), "role": "director"},
            {"email": "manager@retailgpt.com", "username": "manager", "full_name": "Inventory Manager", "hashed_pw": hash_password("manager123"), "role": "manager"},
            {"email": "planner@retailgpt.com", "username": "planner", "full_name": "Inventory Planner", "hashed_pw": hash_password("planner123"), "role": "planner"},
        ]
        for u_data in users_data:
            user = User(**u_data)
            db.add(user)

        # 3. Seed Suppliers
        suppliers_data = [
            {"name": "Global Logistics Corp", "lead_time_days": 5, "reliability_score": 96.5, "fill_rate": 98.2, "contact_info": "orders@globallogistics.com"},
            {"name": "Delta Distributors", "lead_time_days": 8, "reliability_score": 91.0, "fill_rate": 94.5, "contact_info": "sales@deltadist.com"},
            {"name": "Apex Wholesale", "lead_time_days": 3, "reliability_score": 98.8, "fill_rate": 99.1, "contact_info": "support@apexwholesale.com"},
            {"name": "Apex Pharma Solutions", "lead_time_days": 4, "reliability_score": 98.0, "fill_rate": 97.4, "contact_info": "b2b@apexpharma.com"},
            {"name": "FMCG FastPack", "lead_time_days": 6, "reliability_score": 94.2, "fill_rate": 96.0, "contact_info": "wholesale@fmcgfast.com"},
        ]
        suppliers_list = []
        for s_data in suppliers_data:
            supplier = Supplier(**s_data)
            db.add(supplier)
            db.flush()
            suppliers_list.append(supplier)

        # 4. Seed Warehouses
        warehouses_data = [
            {"name": "Warehouse A", "location": "North Regional Hub (Delhi)", "capacity": 15000.0, "utilization": 42.5},
            {"name": "Warehouse B", "location": "South Fulfillment Center (Bengaluru)", "capacity": 20000.0, "utilization": 58.0},
            {"name": "Warehouse C", "location": "West Coast Terminal (Mumbai)", "capacity": 10000.0, "utilization": 29.5},
        ]
        warehouses_list = []
        for w_data in warehouses_data:
            warehouse = Warehouse(**w_data)
            db.add(warehouse)
            db.flush()
            warehouses_list.append(warehouse)

        # 5. Seed Products
        products_data = [
            {"sku": "SKU-101", "name": "Organic Energy Drink 250ml", "category": "Beverages", "subcategory": "Energy Drinks", "base_price": 150.0, "unit_cost": 60.0, "lead_time_days": 5, "safety_stock": 50.0, "reorder_point": 150.0, "abc_class": "A", "supplier_id": suppliers_list[1].id},
            {"sku": "SKU-205", "name": "Spiced Potato Chips 150g", "category": "Snacks", "subcategory": "Chips", "base_price": 80.0, "unit_cost": 30.0, "lead_time_days": 3, "safety_stock": 40.0, "reorder_point": 120.0, "abc_class": "B", "supplier_id": suppliers_list[0].id},
            {"sku": "SKU-330", "name": "Moisturizing Face Wash 100ml", "category": "Personal Care", "subcategory": "Skincare", "base_price": 299.0, "unit_cost": 120.0, "lead_time_days": 7, "safety_stock": 30.0, "reorder_point": 90.0, "abc_class": "A", "supplier_id": suppliers_list[2].id},
            {"sku": "SKU-440", "name": "Eco-Friendly Laundry Detergent 1L", "category": "Home Care", "subcategory": "Cleaning", "base_price": 450.0, "unit_cost": 200.0, "lead_time_days": 6, "safety_stock": 25.0, "reorder_point": 75.0, "abc_class": "B", "supplier_id": suppliers_list[1].id},
            {"sku": "SKU-555", "name": "Whole Wheat Sliced Bread 400g", "category": "Packaged Food", "subcategory": "Bakery", "base_price": 60.0, "unit_cost": 25.0, "lead_time_days": 2, "safety_stock": 60.0, "reorder_point": 180.0, "abc_class": "A", "supplier_id": suppliers_list[4].id},
            {"sku": "SKU-601", "name": "Premium Whey Protein Chocolate 1kg", "category": "Nutrition", "subcategory": "Supplements", "base_price": 2499.0, "unit_cost": 1200.0, "lead_time_days": 10, "safety_stock": 15.0, "reorder_point": 45.0, "abc_class": "A", "supplier_id": suppliers_list[0].id},
            {"sku": "SKU-702", "name": "Paracetamol 500mg (100 Tabs)", "category": "Pharmacy", "subcategory": "OTC", "base_price": 45.0, "unit_cost": 12.0, "lead_time_days": 4, "safety_stock": 100.0, "reorder_point": 300.0, "abc_class": "B", "supplier_id": suppliers_list[3].id},
            {"sku": "SKU-810", "name": "Wireless Noise-Cancelling Headphones", "category": "Electronics", "subcategory": "Audio", "base_price": 3999.0, "unit_cost": 1800.0, "lead_time_days": 12, "safety_stock": 10.0, "reorder_point": 30.0, "abc_class": "C", "supplier_id": suppliers_list[0].id},
        ]
        products_list = []
        for p_data in products_data:
            product = Product(**p_data)
            db.add(product)
            db.flush()
            products_list.append(product)

        # 6. Seed Inventory (Stock levels per SKU per Warehouse)
        # We will create some overstock and understock situations
        inventory_overrides = {
            "SKU-101": [5.0, 10.0, 8.0],     # Critically low everywhere (Understock)
            "SKU-205": [800.0, 950.0, 100.0], # Massive overstock in A/B
            "SKU-330": [10.0, 140.0, 20.0],  # Critical in A/C
            "SKU-440": [80.0, 95.0, 85.0],    # Healthy
            "SKU-555": [20.0, 30.0, 25.0],    # Understock
            "SKU-601": [50.0, 45.0, 48.0],    # Healthy
            "SKU-702": [350.0, 400.0, 380.0], # Healthy
            "SKU-810": [2.0, 3.0, 1.0],       # Near Stockout
        }

        for prod in products_list:
            stocks = inventory_overrides.get(prod.sku, [100.0, 100.0, 100.0])
            for i, wh in enumerate(warehouses_list):
                inv = InventoryItem(
                    product_id=prod.id,
                    warehouse_id=wh.id,
                    current_stock=stocks[i],
                    minimum_order_qty=20.0 if prod.category != "Electronics" else 5.0
                )
                db.add(inv)

        # 7. Seed Sales History & Forecasts (Past 90 days sales, next 30 days forecasts)
        rng = random.Random(42)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=90)

        print("[DATA] Generating transaction and forecast records...")
        for prod in products_list:
            base_sales = {
                "SKU-101": 25, "SKU-205": 40, "SKU-330": 15, "SKU-440": 12,
                "SKU-555": 80, "SKU-601": 8, "SKU-702": 50, "SKU-810": 3
            }.get(prod.sku, 20)

            # Seed Sales
            current_date = start_date
            while current_date <= end_date:
                # Add weekly cycle and seasonality
                weekday = current_date.weekday()
                multiplier = 1.3 if weekday in [4, 5] else 0.9  # higher sales on weekends
                noise = rng.uniform(0.8, 1.2)
                qty = max(1, int(base_sales * multiplier * noise))

                # distribute sales randomly across warehouses
                for wh in warehouses_list:
                    wh_qty = max(0, int(qty / 3 + rng.randint(-2, 2)))
                    if wh_qty > 0:
                        sale = Sale(
                            product_id=prod.id,
                            warehouse_id=wh.id,
                            quantity=wh_qty,
                            price=prod.base_price,
                            cost=prod.unit_cost,
                            transaction_date=datetime.combine(current_date, datetime.min.time())
                        )
                        db.add(sale)
                current_date += timedelta(days=1)

            # Seed Forecasts (Next 30 days)
            forecast_start = end_date + timedelta(days=1)
            for day in range(30):
                f_date = forecast_start + timedelta(days=day)
                weekday = f_date.weekday()
                multiplier = 1.3 if weekday in [4, 5] else 0.9
                expected_demand = base_sales * multiplier * rng.uniform(0.9, 1.1)

                forecast = Forecast(
                    product_id=prod.id,
                    forecast_date=datetime.combine(f_date, datetime.min.time()),
                    expected_demand=round(expected_demand, 1),
                    forecast_confidence=rng.uniform(78.0, 95.0),
                    accuracy=rng.uniform(82.0, 96.0)
                )
                db.add(forecast)

        db.flush()

        # 8. Seed Risk Scores (Computed decision engine values)
        # Core calculations:
        # SKU-101: critical stockout, SKU-205: overstock, SKU-330: medium risk, SKU-810: high stockout risk
        for prod in products_list:
            total_stock = db.query(InventoryItem.current_stock).filter(InventoryItem.product_id == prod.id).all()
            current_stock_sum = sum([s[0] for s in total_stock])

            # 30-day forecast sum
            forecasts_30 = db.query(Forecast.expected_demand).filter(
                Forecast.product_id == prod.id,
                Forecast.forecast_date > datetime.utcnow()
            ).all()
            forecast_sum = sum([f[0] for f in forecasts_30]) or 300.0
            avg_daily_sales = forecast_sum / 30.0

            days_of_cover = current_stock_sum / avg_daily_sales if avg_daily_sales > 0 else 999.0
            inventory_gap = max(0, forecast_sum - current_stock_sum)
            revenue_risk = inventory_gap * prod.base_price
            profit_risk = inventory_gap * (prod.base_price - prod.unit_cost)

            # Determine action details
            if days_of_cover < 7:
                action = "Order Now"
                urgency = 0.95
                severity = 1  # Critical
                root_causes = ["Stockout Imminent", f"Low Days of Cover ({days_of_cover:.1f} days)", "High Demand Velocity"]
                reorder_qty = round(forecast_sum * 1.5 - current_stock_sum)
            elif days_of_cover < 14:
                action = "Increase Order"
                urgency = 0.75
                severity = 2  # High
                root_causes = ["Reorder Threshold Triggered", "Lead Time Delay Vulnerability"]
                reorder_qty = round(forecast_sum * 1.2 - current_stock_sum)
            elif current_stock_sum > forecast_sum * 1.8:
                action = "Liquidate Excess"
                urgency = 0.70
                severity = 2  # High (carrying cost exposure)
                root_causes = ["Overstock", "High Carrying Costs", "Forecast Variance Drop"]
                reorder_qty = 0.0
                carrying_cost = (current_stock_sum - forecast_sum) * prod.unit_cost * 0.25
                revenue_risk = 0.0
                profit_risk = carrying_cost  # Cost savings potential instead of loss
            else:
                action = "Monitor"
                urgency = 0.15
                severity = 4  # Low
                root_causes = ["Stock Levels Healthy"]
                reorder_qty = 0.0
                revenue_risk = 0.0
                profit_risk = 0.0

            risk = RiskScore(
                product_id=prod.id,
                revenue_at_risk=round(revenue_risk, 2),
                profit_at_risk=round(profit_risk, 2),
                financial_priority=severity,
                forecast_confidence=round(prod.forecasts[0].forecast_confidence, 1) if prod.forecasts else 88.5,
                expected_stockout_days=round(max(0.0, 7.0 - days_of_cover), 1) if days_of_cover < 7 else 0.0,
                recommended_action=action,
                urgency=urgency,
                root_causes=root_causes,
                service_level=98.5 if prod.abc_class == "A" else 95.0,
                reorder_quantity=float(max(0, reorder_qty))
            )
            db.add(risk)

        # 9. Seed Alerts
        alerts_data = [
            {"product_id": products_list[0].id, "type": "Stockout Risk", "message": "SKU-101 has critically low stock (23 units left) across all locations with only 1.2 days of cover.", "severity": "Critical", "status": "Active"},
            {"product_id": products_list[7].id, "type": "Stockout Risk", "message": "SKU-810 has critically low stock (6 units left). Stockout expected in 2.1 days.", "severity": "Critical", "status": "Active"},
            {"product_id": products_list[2].id, "type": "Supplier Delay", "message": "Apex Wholesale reported a 3-day transit delay for SKU-330 order. Revenue exposure: ₹45,000.", "severity": "High", "status": "Active"},
            {"product_id": products_list[1].id, "type": "Overstock Alert", "message": "SKU-205 current stock (1,850 units) exceeds 60-day forecast by 250%. Carrying cost at risk.", "severity": "Medium", "status": "Active"},
        ]
        for a_data in alerts_data:
            alert = Alert(**a_data)
            db.add(alert)

        # 10. Seed Purchase Orders
        po_data = [
            {
                "supplier_id": suppliers_list[1].id,
                "status": "In Transit",
                "total_cost": 60000.0,
                "expected_delivery_date": datetime.utcnow() + timedelta(days=2),
                "details": [{"sku": "SKU-101", "quantity": 1000, "unit_cost": 60.0}]
            },
            {
                "supplier_id": suppliers_list[2].id,
                "status": "Draft",
                "total_cost": 24000.0,
                "expected_delivery_date": datetime.utcnow() + timedelta(days=5),
                "details": [{"sku": "SKU-330", "quantity": 200, "unit_cost": 120.0}]
            },
            {
                "supplier_id": suppliers_list[0].id,
                "status": "Delivered",
                "total_cost": 45000.0,
                "expected_delivery_date": datetime.utcnow() - timedelta(days=3),
                "details": [{"sku": "SKU-205", "quantity": 1500, "unit_cost": 30.0}]
            }
        ]
        for p_po in po_data:
            po = PurchaseOrder(**p_po)
            db.add(po)

        # 11. Seed Transfers
        transfer = InventoryTransfer(
            from_warehouse_id=warehouses_list[1].id,
            to_warehouse_id=warehouses_list[0].id,
            product_id=products_list[1].id,
            quantity=150.0,
            status="Shipped",
            transfer_date=datetime.utcnow() - timedelta(hours=12)
        )
        db.add(transfer)

        # 12. Audit Logs
        log = AuditLog(
            user="system",
            action="seed",
            resource="database",
            detail="System database initial seeding completed.",
            ip_address="127.0.0.1"
        )
        db.add(log)

        db.commit()
        print("[SUCCESS] Seeding completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error during seeding: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_BACKEND = ROOT_DIR / "backend"
sys.path.insert(0, str(WORKSPACE_BACKEND))

from database.models import (
    Alert,
    Forecast,
    InventoryItem,
    Product,
    PurchaseOrder,
    RiskScore,
)
from database.session import SessionLocal


def get_db_evidence():
    db = SessionLocal()
    print("=== LIVE DATABASE EVIDENCE FOR SKU-101 ===")

    # Product Catalog Info
    p = db.query(Product).filter(Product.sku == "SKU-101").first()
    if p:
        print("\n--- 1. Products Table Record ---")
        p_dict = {
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "unit_cost": float(p.unit_cost) if p.unit_cost else None,
            "unit_price": float(p.base_price) if p.base_price else None,
            "safety_stock": float(p.safety_stock) if p.safety_stock else None,
            "reorder_point": float(p.reorder_point) if p.reorder_point else None,
        }
        print(json.dumps(p_dict, indent=2))

        # Inventory levels
        inv_items = (
            db.query(InventoryItem).filter(InventoryItem.product_id == p.id).all()
        )
        print("\n--- 2. Inventory Table Records (Warehouse levels) ---")
        inv_list = []
        for item in inv_items:
            inv_list.append(
                {
                    "id": item.id,
                    "warehouse_id": item.warehouse_id,
                    "warehouse_name": item.warehouse.name,
                    "current_stock": float(item.current_stock),
                }
            )
        print(json.dumps(inv_list, indent=2))

        # Forecasts
        fc_count = db.query(Forecast).filter(Forecast.product_id == p.id).count()
        fc_samples = (
            db.query(Forecast).filter(Forecast.product_id == p.id).limit(5).all()
        )
        print(f"\n--- 3. Forecasts Table Records (Count: {fc_count}) ---")
        fc_list = []
        for f in fc_samples:
            fc_list.append(
                {
                    "id": f.id,
                    "forecast_date": (
                        f.forecast_date.date().isoformat() if f.forecast_date else None
                    ),
                    "forecasted_quantity": float(f.expected_demand),
                    "confidence_interval_upper": (
                        float(f.forecast_confidence) if f.forecast_confidence else None
                    ),
                }
            )
        print("Sample Forecast Rows:")
        print(json.dumps(fc_list, indent=2))

        # Risk Score
        risk = db.query(RiskScore).filter(RiskScore.product_id == p.id).first()
        print("\n--- 4. Risk Scores Table Record ---")
        if risk:
            risk_dict = {
                "id": risk.id,
                "expected_stockout_days": (
                    float(risk.expected_stockout_days)
                    if risk.expected_stockout_days
                    else None
                ),
                "revenue_at_risk": (
                    float(risk.revenue_at_risk) if risk.revenue_at_risk else None
                ),
                "profit_at_risk": (
                    float(risk.profit_at_risk) if risk.profit_at_risk else None
                ),
                "reorder_quantity": (
                    float(risk.reorder_quantity) if risk.reorder_quantity else None
                ),
                "financial_priority": risk.financial_priority,
            }
            print(json.dumps(risk_dict, indent=2))
        else:
            print("No risk score record found.")

        # Alerts
        alerts = db.query(Alert).filter(Alert.product_id == p.id).all()
        print("\n--- 5. Alerts Table Records (Active/Resolved) ---")
        alert_list = []
        for a in alerts:
            alert_list.append(
                {
                    "id": a.id,
                    "alert_type": a.type,
                    "message": a.message,
                    "status": a.status,
                    "severity": a.severity,
                }
            )
        print(json.dumps(alert_list, indent=2))

        # Purchase Orders referencing SKU-101
        pos = db.query(PurchaseOrder).all()
        print("\n--- 6. Purchase Orders Reference Records ---")
        po_list = []
        for po in pos:
            # Check if SKU-101 is in PO details
            po_details = po.details
            contains_sku = False
            if po_details:
                for item in po_details:
                    if item.get("sku") == "SKU-101":
                        contains_sku = True
                        break
            if contains_sku:
                po_list.append(
                    {
                        "id": po.id,
                        "po_number": f"PO-{po.id}",
                        "status": po.status,
                        "total_cost": float(po.total_cost),
                        "created_at": (
                            po.created_at.date().isoformat() if po.created_at else None
                        ),
                    }
                )
        print(json.dumps(po_list, indent=2))

    db.close()


if __name__ == "__main__":
    get_db_evidence()

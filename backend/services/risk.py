from typing import List, Dict
from sqlalchemy.orm import Session
from database.models import SalesRecord, InventoryRecord


    risks.append({
        "sku": sale.sku,
        "demand": sale.demand,
        "inventory": inv.inventory,
        "unit_price": inv.unit_price,
        "risk_amount": round(risk_amount, 2),
        "reason": f"Inventory ({inv.inventory}) < 80% of demand ({sale.demand})",
        "recommended_quantity": int(sale.demand - inv.inventory),
        "supplier_name": "Default Supplier",
        "expected_cost": round((sale.demand - inv.inventory) * inv.unit_price, 2),
    })
    for sale in sales:
        inv = db.query(InventoryRecord).filter_by(sku=sale.sku).first()
        if not inv:
            continue
        if inv.inventory < sale.demand * 0.8:
            risk_amount = (sale.demand - inv.inventory) * inv.unit_price
            risks.append({
                "sku": sale.sku,
                "demand": sale.demand,
                "inventory": inv.inventory,
                "unit_price": inv.unit_price,
                "risk_amount": round(risk_amount, 2),
                "reason": f"Inventory ({inv.inventory}) < 80% of demand ({sale.demand})",
            })
    return risks

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app import app
from backend.database.session import SessionLocal
from backend.database.models import Product, Warehouse, InventoryItem, Forecast, Alert, RiskScore
from datetime import datetime, timedelta

client = TestClient(app)

def test_warehouse_optimizer_integration():
    # 1. Login to get headers
    register_payload = {
        "email": "opt_tester@retailgpt.com",
        "username": "opt_tester",
        "full_name": "Optimizer Tester",
        "password": "testpassword123",
        "role": "admin"
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post("/api/auth/login", data={"username": "opt_tester", "password": "testpassword123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    
    # 2. Setup mock warehouses A & B, product SKU-BAL-888
    wh_a = db.query(Warehouse).filter(Warehouse.name == "Warehouse A").first()
    wh_b = db.query(Warehouse).filter(Warehouse.name == "Warehouse B").first()
    
    if not wh_a:
        wh_a = Warehouse(name="Warehouse A", capacity=10000.0, utilization=0.0)
        db.add(wh_a)
        db.flush()
    if not wh_b:
        wh_b = Warehouse(name="Warehouse B", capacity=10000.0, utilization=0.0)
        db.add(wh_b)
        db.flush()

    # Clean up old mock product if existing
    existing = db.query(Product).filter(Product.sku == "SKU-BAL-888").first()
    if existing:
        db.query(Forecast).filter(Forecast.product_id == existing.id).delete()
        db.query(InventoryItem).filter(InventoryItem.product_id == existing.id).delete()
        db.query(Product).filter(Product.id == existing.id).delete()
        db.commit()

    prod = Product(
        sku="SKU-BAL-888",
        name="Balancing Test Chips",
        category="Snacks",
        base_price=100.0,
        unit_cost=40.0,
        lead_time_days=3,
        safety_stock=50.0,      # Safety stock target
        reorder_point=100.0,
        abc_class="B"
    )
    db.add(prod)
    db.flush()

    # Deficit at Warehouse A (10 units, safety stock is 50 -> deficit of 40)
    inv_a = InventoryItem(product_id=prod.id, warehouse_id=wh_a.id, current_stock=10.0)
    # Surplus at Warehouse B (300 units, safety stock is 50 + 30d forecast of 100 -> surplus of 150)
    inv_b = InventoryItem(product_id=prod.id, warehouse_id=wh_b.id, current_stock=300.0)
    db.add(inv_a)
    db.add(inv_b)

    # 30-day forecast is 100 units total (daily demand of ~3.3 units)
    for i in range(30):
        f = Forecast(
            product_id=prod.id,
            forecast_date=datetime.utcnow() + timedelta(days=i+1),
            expected_demand=3.3,
            forecast_confidence=90.0,
            accuracy=90.0
        )
        db.add(f)
    db.commit()

    try:
        # 3. Call warehouses optimization endpoint
        response = client.get("/api/enterprise/warehouses", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify that a suggested transfer is dynamically generated for SKU-BAL-888
        transfers = data["suggested_transfers"]
        assert len(transfers) > 0
        
        # Look for our specific product in suggested transfers
        our_transfer = None
        for t in transfers:
            if t["sku"] == "SKU-BAL-888":
                our_transfer = t
                break
                
        assert our_transfer is not None
        assert our_transfer["from_warehouse"] == "Warehouse B"
        assert our_transfer["to_warehouse"] == "Warehouse A"
        # Min of surplus (150) and deficit (40) is 40 units
        assert our_transfer["quantity"] == 40.0
        assert our_transfer["financial_impact"] == 4000.0 # 40 units * 100.0 price
        
    finally:
        # Cleanup
        db.query(Forecast).filter(Forecast.product_id == prod.id).delete()
        db.query(InventoryItem).filter(InventoryItem.product_id == prod.id).delete()
        db.query(Product).filter(Product.id == prod.id).delete()
        
        from backend.database.models import User
        user = db.query(User).filter(User.username == "opt_tester").first()
        if user:
            db.delete(user)
        db.commit()
        db.close()

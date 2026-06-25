from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app import app
from backend.database.models import AuditLog, InventoryItem, User
from backend.database.session import SessionLocal

client = TestClient(app)


def test_erp_pos_sync_integration():
    # 1. Register and Login to get token headers
    register_payload = {
        "email": "sync_tester@retailgpt.com",
        "username": "sync_tester",
        "full_name": "Sync Tester",
        "password": "testpassword123",
        "role": "admin",
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "sync_tester", "password": "testpassword123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()

    try:
        # 2. Get initial stock level count or list
        items_before = db.query(InventoryItem).all()
        assert len(items_before) > 0

        # 3. Call sync Shopify endpoint
        response = client.post("/api/enterprise/sync/shopify", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["platform"] == "shopify"
        assert "synced_records" in data
        assert "total_inventory_value" in data

        # 4. Call sync status history endpoint
        status_resp = client.get("/api/enterprise/sync/status", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert len(status_data) > 0
        assert status_data[0]["platform"] == "SHOPIFY"
        assert "Synced inventory stock levels from SHOPIFY" in status_data[0]["detail"]
        assert status_data[0]["operator"] == "sync_tester"

        # 5. Call invalid platform to verify validation error
        invalid_resp = client.post(
            "/api/enterprise/sync/invalidplatform", headers=headers
        )
        assert invalid_resp.status_code == 400
        assert "Unsupported ERP/POS platform" in invalid_resp.json()["detail"]

    finally:
        # Cleanup
        db.query(AuditLog).filter(AuditLog.user == "sync_tester").delete()
        user = db.query(User).filter(User.username == "sync_tester").first()
        if user:
            db.delete(user)
        db.commit()
        db.close()

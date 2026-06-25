from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.database.models import (
    Product,
    User,
    AuditLog,
    InventoryItem,
    Warehouse,
    InventoryTransfer,
    Supplier,
    PurchaseOrder,
    RiskScore,
)
from backend.database.session import SessionLocal

from backend.app import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    # Ensure tables are created and database is seeded cleanly
    from backend.database.intelligence import Base as IntelBase
    from backend.database.models import Base as ModelsBase
    from backend.database.seed_db import seed_all
    from backend.database.session import create_tables, engine

    # Drop all tables first for a clean state
    ModelsBase.metadata.drop_all(bind=engine)
    IntelBase.metadata.drop_all(bind=engine)
    create_tables()
    seed_all()

    # 1. Register a test user
    register_payload = {
        "email": "test_enterprise@retailgpt.com",
        "username": "test_ent_user",
        "full_name": "Test Enterprise User",
        "password": "testpassword123",
        "role": "admin",
    }
    # Clean up existing test user if any
    db = SessionLocal()
    existing = (
        db.query(User).filter(User.username == register_payload["username"]).first()
    )
    if existing:
        db.delete(existing)
        db.commit()
    db.close()

    client.post("/api/auth/register", json=register_payload)

    # 2. Log in to get token
    login_payload = {"username": "test_ent_user", "password": "testpassword123"}
    response = client.post("/api/auth/login", data=login_payload)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_executive_briefing(auth_headers):
    response = client.get("/api/enterprise/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "revenue_at_risk" in data
    assert "profit_at_risk" in data
    assert "top_threatened" in data
    assert "executive_feed" in data


def test_action_center_list(auth_headers):
    response = client.get("/api/enterprise/decisions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "sku" in item
        assert "revenue_impact" in item
        assert "recommended_action" in item


def test_assign_and_status_updates(auth_headers):
    # Get first SKU from decisions
    response = client.get("/api/enterprise/decisions", headers=auth_headers)
    decisions = response.json()
    if not decisions:
        return

    sku = decisions[0]["sku"]

    # Assign SKU
    assign_resp = client.post(
        f"/api/enterprise/decisions/{sku}/assign",
        json={"username": "test_ent_user"},
        headers=auth_headers,
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["success"] is True

    # Update status
    status_resp = client.post(
        f"/api/enterprise/decisions/{sku}/status",
        json={"status": "In Progress"},
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["success"] is True

    # Add note
    note_resp = client.post(
        f"/api/enterprise/decisions/{sku}/notes",
        json={"note": "Verified lead times with supplier. Ordering delayed items."},
        headers=auth_headers,
    )
    assert note_resp.status_code == 200


def test_inventory_control_tower(auth_headers):
    response = client.get("/api/enterprise/control-tower", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "understock" in data
    assert "overstock" in data
    assert "dead_inventory" in data
    assert "fast_movers" in data


def test_reorder_engine(auth_headers):
    response = client.get("/api/enterprise/reorder", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        item = data[0]
        assert "eoq" in item
        assert "safety_stock" in item
        assert "reorder_point" in item
        assert "priority_score" in item
        assert "supplier_name" in item
        assert "unit_cost" in item
        assert "purchase_cost" in item
        assert "category" in item


def test_revenue_protection(auth_headers):
    response = client.get("/api/enterprise/revenue-protection", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "revenue_at_risk" in data
    assert "revenue_saved_by_actions" in data
    assert "top_threatened_products" in data


def test_product_intelligence_sku(auth_headers):
    response = client.get("/api/enterprise/sku/SKU-101", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sku"] == "SKU-101"
    assert "WHAT_IS_HAPPENING" in data
    assert "WHY_IT_IS_HAPPENING" in data
    assert "WHAT_SHOULD_BE_DONE" in data
    assert "FINANCIAL_IMPACT" in data
    assert "EXECUTIVE_RECOMMENDATION" in data


def test_forecast_quality(auth_headers):
    response = client.get("/api/enterprise/forecast-quality", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "forecast_confidence" in data
    assert "forecast_accuracy" in data
    assert "model_selection" in data


def test_ai_decision_copilot(auth_headers):
    # Test typical question
    response = client.post(
        "/api/enterprise/copilot/chat",
        json={"prompt": "What should I order today?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "insight" in data
    assert "recommendation" in data
    assert "financial_impact" in data


def test_abc_inventory_analysis(auth_headers):
    response = client.get("/api/enterprise/abc-analysis", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "A" in data
    assert "B" in data
    assert "C" in data


def test_supplier_intelligence(auth_headers):
    response = client.get("/api/enterprise/suppliers", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "reliability_score" in data[0]
        assert "fill_rate" in data[0]


def test_multi_warehouse_optimization(auth_headers):
    response = client.get("/api/enterprise/warehouses", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "warehouses" in data
    assert "suggested_transfers" in data


def test_alerting_system(auth_headers):
    response = client.get("/api/enterprise/alerts", headers=auth_headers)
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)

    if len(alerts) > 0:
        alert_id = alerts[0]["id"]
        resolve_resp = client.post(
            f"/api/enterprise/alerts/{alert_id}/resolve", headers=auth_headers
        )
        assert resolve_resp.status_code == 200
        assert resolve_resp.json()["success"] is True


def test_purchase_order_automation(auth_headers):
    response = client.get("/api/enterprise/purchase-orders", headers=auth_headers)
    assert response.status_code == 200
    pos = response.json()
    assert isinstance(pos, list)

    # Find draft PO
    draft_po_id = None
    for po in pos:
        if po["status"] == "Draft":
            draft_po_id = po["id"]
            break

    if draft_po_id:
        approve_resp = client.post(
            f"/api/enterprise/purchase-orders/{draft_po_id}/approve",
            headers=auth_headers,
        )
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "Approved"


def test_role_based_financial_gating(auth_headers):
    # 1. Register test users for different roles
    client.post(
        "/api/auth/register",
        json={
            "email": "planner_test@retailgpt.com",
            "username": "planner_user",
            "full_name": "Planner User",
            "password": "plannerpassword",
            "role": "planner",
        },
    )
    client.post(
        "/api/auth/register",
        json={
            "email": "manager_test@retailgpt.com",
            "username": "manager_user",
            "full_name": "Manager User",
            "password": "managerpassword",
            "role": "manager",
        },
    )
    client.post(
        "/api/auth/register",
        json={
            "email": "director_test@retailgpt.com",
            "username": "director_user",
            "full_name": "Director User",
            "password": "directorpassword",
            "role": "director",
        },
    )

    # Get login headers
    planner_resp = client.post(
        "/api/auth/login",
        data={"username": "planner_user", "password": "plannerpassword"},
    )
    planner_headers = {"Authorization": f"Bearer {planner_resp.json()['access_token']}"}

    manager_resp = client.post(
        "/api/auth/login",
        data={"username": "manager_user", "password": "managerpassword"},
    )
    manager_headers = {"Authorization": f"Bearer {manager_resp.json()['access_token']}"}

    director_resp = client.post(
        "/api/auth/login",
        data={"username": "director_user", "password": "directorpassword"},
    )
    director_headers = {
        "Authorization": f"Bearer {director_resp.json()['access_token']}"
    }

    # 2. Create a high cost PO (total cost: ₹150,000)
    # Unit cost of SKU-101 is 60. Quantity of 2500 units makes it 150,000
    create_payload = {"supplier_id": 1, "items": [{"sku": "SKU-101", "quantity": 2500}]}
    po_resp = client.post(
        "/api/enterprise/purchase-orders/create",
        json=create_payload,
        headers=planner_headers,
    )
    assert po_resp.status_code == 200
    po_id = po_resp.json()["po_id"]
    assert po_resp.json()["total_cost"] == 150000.0

    # 3. Planner submits PO for approval
    submit_resp = client.post(
        f"/api/enterprise/purchase-orders/{po_id}/submit", headers=planner_headers
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "Pending Approval"

    # 4. Planner attempts to approve PO -> should fail 403
    app_plan = client.post(
        f"/api/enterprise/purchase-orders/{po_id}/approve", headers=planner_headers
    )
    assert app_plan.status_code == 403
    assert "not authorized for this action" in app_plan.json()["detail"]

    # 5. Manager attempts to approve PO of 150,000 -> should fail 403 (limit is 100k)
    app_mgr = client.post(
        f"/api/enterprise/purchase-orders/{po_id}/approve", headers=manager_headers
    )
    assert app_mgr.status_code == 403
    assert "exceeds approval limit" in app_mgr.json()["detail"]

    # 6. Director attempts to approve PO of 150,000 -> should succeed (limit is 500k)
    app_dir = client.post(
        f"/api/enterprise/purchase-orders/{po_id}/approve", headers=director_headers
    )
    assert app_dir.status_code == 200
    assert app_dir.json()["status"] == "Approved"

    # 7. Check audit log has records
    db = SessionLocal()
    from backend.database.models import AuditLog

    audits = db.query(AuditLog).filter(AuditLog.resource == f"PO {po_id}").all()
    assert len(audits) >= 3  # create, submit, approve
    db.close()


def test_two_way_integration_service(auth_headers):
    # 1. Create a draft PO
    planner_resp = client.post(
        "/api/auth/login",
        data={"username": "planner_user", "password": "plannerpassword"},
    )
    planner_headers = {"Authorization": f"Bearer {planner_resp.json()['access_token']}"}

    create_payload = {"supplier_id": 1, "items": [{"sku": "SKU-101", "quantity": 10}]}
    po_resp = client.post(
        "/api/enterprise/purchase-orders/create",
        json=create_payload,
        headers=planner_headers,
    )
    po_id = po_resp.json()["po_id"]

    # 2. Approve PO with director role (value = 600, well below limits)
    director_resp = client.post(
        "/api/auth/login",
        data={"username": "director_user", "password": "directorpassword"},
    )
    director_headers = {
        "Authorization": f"Bearer {director_resp.json()['access_token']}"
    }

    app_resp = client.post(
        f"/api/enterprise/purchase-orders/{po_id}/approve", headers=director_headers
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "Approved"

    # 3. Check db logs for PO sync
    db = SessionLocal()
    # from database.models import AuditLog # Already imported

    shopify_po_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource == f"PO {po_id}", AuditLog.action == "shopify_sync_po"
        )
        .first()
    )
    assert shopify_po_log is not None
    assert "Shopify Order ID 89472938472" in shopify_po_log.detail

    zoho_po_log = (
        db.query(AuditLog)
        .filter(AuditLog.resource == f"PO {po_id}", AuditLog.action == "zoho_sync_po")
        .first()
    )
    assert zoho_po_log is not None
    assert "Zoho PO ID zoho_po_987654" in zoho_po_log.detail

    # 4. Trigger stock transfer
    transfer_payload = {
        "from_wh": "Warehouse B",
        "to_wh": "Warehouse A",
        "sku": "SKU-205",
        "quantity": 20,
    }
    trans_resp = client.post(
        "/api/enterprise/transfers", json=transfer_payload, headers=director_headers
    )
    assert trans_resp.status_code == 200

    # Check that stock was adjusted correctly immediately (conserving stock)
    # from database.models import InventoryItem, Warehouse # Already imported

    wh_a = db.query(Warehouse).filter(Warehouse.name == "Warehouse A").first()
    wh_b = db.query(Warehouse).filter(Warehouse.name == "Warehouse B").first()
    prod_205 = db.query(Product).filter(Product.sku == "SKU-205").first()

    inv_a = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod_205.id,
            InventoryItem.warehouse_id == wh_a.id,
        )
        .first()
    )
    inv_b = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod_205.id,
            InventoryItem.warehouse_id == wh_b.id,
        )
        .first()
    )

    assert inv_b.current_stock == 930.0
    assert inv_a.current_stock == 820.0

    # 5. Check db logs for transfer sync
    # from database.models import InventoryTransfer # Already imported

    latest_transfer = (
        db.query(InventoryTransfer).order_by(InventoryTransfer.id.desc()).first()
    )
    assert latest_transfer is not None
    assert latest_transfer.status == "Pending"

    shopify_tr_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource == f"Transfer {latest_transfer.id}",
            AuditLog.action == "shopify_sync_transfer",
        )
        .first()
    )
    assert shopify_tr_log is not None
    assert "Adjusted Shopify Location 98452" in shopify_tr_log.detail

    zoho_tr_log = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource == f"Transfer {latest_transfer.id}",
            AuditLog.action == "zoho_sync_transfer",
        )
        .first()
    )
    assert zoho_tr_log is not None
    assert f"Created Zoho Transfer Order TO-{latest_transfer.id}" in zoho_tr_log.detail

    # 6. Receive the transfer using the new endpoint
    receive_resp = client.post(
        f"/api/enterprise/transfers/{latest_transfer.id}/receive",
        headers=director_headers,
    )
    assert receive_resp.status_code == 200

    # Check that transfer status is updated to Received
    db.refresh(latest_transfer)
    assert latest_transfer.status == "Received"

    db.close()


def test_decision_quantity_update(auth_headers):
    # Success case
    resp = client.post(
        "/api/enterprise/decisions/SKU-101/quantity",
        json={"quantity": 500.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["reorder_quantity"] == 500.0

    # Validation failure: negative quantity
    resp_neg = client.post(
        "/api/enterprise/decisions/SKU-101/quantity",
        json={"quantity": -5.0},
        headers=auth_headers,
    )
    assert resp_neg.status_code == 400

    # Validation failure: zero quantity
    resp_zero = client.post(
        "/api/enterprise/decisions/SKU-101/quantity",
        json={"quantity": 0},
        headers=auth_headers,
    )
    assert resp_zero.status_code == 400

    # SKU not found
    resp_missing = client.post(
        "/api/enterprise/decisions/SKU-MISSING/quantity",
        json={"quantity": 100},
        headers=auth_headers,
    )
    assert resp_missing.status_code == 404

    # Verify audit log entry
    db = SessionLocal()
    # from database.models import AuditLog # Already imported

    log = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource == "SKU SKU-101", AuditLog.action == "modify_quantity"
        )
        .first()
    )
    assert log is not None
    assert "Modified recommended reorder quantity to 500" in log.detail
    db.close()


def test_rejected_status_transition(auth_headers):
    # Reject status transition
    resp = client.post(
        "/api/enterprise/decisions/SKU-101/status",
        json={"status": "Rejected"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Verify status in database
    db = SessionLocal()
    from backend.database.models import AuditLog, Product, RiskScore

    prod = db.query(Product).filter(Product.sku == "SKU-101").first()
    risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
    assert risk.status == "Rejected"

    # Verify audit log entry
    log_entry = (  # Renamed to avoid conflict with 'log' in _seed_test_data
        db.query(AuditLog)
        .filter(AuditLog.resource == "SKU SKU-101", AuditLog.action == "reject")
        .first()
    )
    assert log_entry is not None
    assert "Changed status to Rejected" in log_entry.detail
    db.close()


def test_decision_notes_retroduction_and_audit(auth_headers):
    # 1. Add a note first
    resp_add = client.post(
        "/api/enterprise/decisions/SKU-101/notes",
        json={"note": "Verification test notes content"},
        headers=auth_headers,
    )
    assert resp_add.status_code == 200

    # 2. Retrieve the notes
    resp_get = client.get(
        "/api/enterprise/decisions/SKU-101/notes", headers=auth_headers
    )
    assert resp_get.status_code == 200
    notes = resp_get.json()
    assert len(notes) >= 1

    # Check notes properties
    matching_note = next(
        (n for n in notes if n["note"] == "Verification test notes content"), None
    )
    assert matching_note is not None
    assert matching_note["user"] == "test_ent_user"
    assert matching_note["action"] == "add_note"
    assert "timestamp" in matching_note

    # SKU not found for notes GET
    resp_missing = client.get(
        "/api/enterprise/decisions/SKU-MISSING/notes", headers=auth_headers
    )
    assert resp_missing.status_code == 404


def test_reorder_safeguards_and_edge_cases(auth_headers):
    # Setup test products in DB
    db = SessionLocal()
    # from database.models import InventoryItem, Product, Supplier, Warehouse # Already imported

    # Ensure test warehouse exists
    wh = db.query(Warehouse).first()
    if not wh:
        wh = Warehouse(
            name="Test Reorder Warehouse", location="Test Loc", capacity=1000.0
        )
        db.add(wh)
        db.commit()

    # 1. Supplier present
    sup1 = Supplier(name="Test Sup Present", lead_time_days=5)
    db.add(sup1)
    db.commit()

    p_sup_present = Product(
        sku="SKU-TEST-SUP-PRES",
        name="Test Sup Present Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=5.0,
        supplier_id=sup1.id,
    )
    db.add(p_sup_present)
    db.commit()
    inv_sup_present = InventoryItem(
        product_id=p_sup_present.id, warehouse_id=wh.id, current_stock=20.0
    )
    db.add(inv_sup_present)
    db.commit()

    # 2. Supplier missing
    p_sup_missing = Product(
        sku="SKU-TEST-SUP-MISS",
        name="Test Sup Missing Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=5.0,
        supplier_id=None,
    )
    db.add(p_sup_missing)
    db.commit()
    inv_sup_missing = InventoryItem(
        product_id=p_sup_missing.id, warehouse_id=wh.id, current_stock=20.0
    )
    db.add(inv_sup_missing)
    db.commit()

    # 3. Unit cost missing
    p_cost_missing = Product(
        sku="SKU-TEST-COST-MISS",
        name="Test Cost Missing Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=None,
        supplier_id=sup1.id,
    )
    db.add(p_cost_missing)
    db.commit()
    inv_cost_missing = InventoryItem(
        product_id=p_cost_missing.id, warehouse_id=wh.id, current_stock=20.0
    )
    db.add(inv_cost_missing)
    db.commit()

    # 4. Reorder point = 0 (low lead time and no sales/forecast)
    p_rop_zero = Product(
        sku="SKU-TEST-ROP-ZERO",
        name="Test ROP Zero Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=5.0,
        supplier_id=None,
        lead_time_days=0,
    )
    db.add(p_rop_zero)
    db.commit()
    inv_rop_zero = InventoryItem(
        product_id=p_rop_zero.id, warehouse_id=wh.id, current_stock=10.0
    )
    db.add(inv_rop_zero)
    db.commit()

    # 5. Stock above reorder point (very high stock)
    p_above_rop = Product(
        sku="SKU-TEST-ABOVE",
        name="Test Above Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=5.0,
        supplier_id=sup1.id,
    )
    db.add(p_above_rop)
    db.commit()
    inv_above_rop = InventoryItem(
        product_id=p_above_rop.id, warehouse_id=wh.id, current_stock=1000.0
    )
    db.add(inv_above_rop)
    db.commit()

    # 6. Stock below reorder point (stock is 0)
    p_below_rop = Product(
        sku="SKU-TEST-BELOW",
        name="Test Below Prod",
        category="Beverages",
        base_price=10.0,
        unit_cost=5.0,
        supplier_id=sup1.id,
    )
    db.add(p_below_rop)
    db.commit()
    inv_below_rop = InventoryItem(
        product_id=p_below_rop.id, warehouse_id=wh.id, current_stock=0.0
    )
    db.add(inv_below_rop)
    db.commit()

    db.close()

    # Query endpoint
    response = client.get("/api/enterprise/reorder", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()

    # Verify Supplier present
    item_pres = next(x for x in items if x["sku"] == "SKU-TEST-SUP-PRES")
    assert item_pres["supplier_name"] == "Test Sup Present"

    # Verify Supplier missing
    item_miss = next(x for x in items if x["sku"] == "SKU-TEST-SUP-MISS")
    assert item_miss["supplier_name"] is None

    # Verify Unit Cost missing
    item_cost = next(x for x in items if x["sku"] == "SKU-TEST-COST-MISS")
    assert item_cost["unit_cost"] == 0.0
    assert item_cost["purchase_cost"] == 0.0

    # Verify Reorder Point = 0
    item_rop = next(x for x in items if x["sku"] == "SKU-TEST-ROP-ZERO")
    assert item_rop["reorder_point"] == 0.0
    assert item_rop["priority_score"] == 0.0

    # Verify Stock above reorder point
    item_above = next(x for x in items if x["sku"] == "SKU-TEST-ABOVE")
    assert item_above["priority_score"] == 0.0

    # Verify Stock below reorder point
    item_below = next(x for x in items if x["sku"] == "SKU-TEST-BELOW")
    if item_below["reorder_point"] > 0:
        assert item_below["priority_score"] == 100.0

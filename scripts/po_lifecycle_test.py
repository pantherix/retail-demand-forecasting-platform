import json
import sys
from pathlib import Path

WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
sys.path.insert(0, str(WORKSPACE_BACKEND))

from backend.app import app
from backend.auth.dependencies import get_current_user
from backend.database.models import PurchaseOrder, User
from backend.database.session import SessionLocal
from fastapi.testclient import TestClient


def test_po_lifecycle():
    from backend.database.session import create_tables
    from backend.database.seed_db import seed_all
    
    create_tables()
    db = SessionLocal()
    print("=== PURCHASE ORDER LIFECYCLE AUDIT ===")

    # 1. Bypass auth as Director (since PO requires manager/director/admin approval)
    director_user = db.query(User).filter(User.username == "director").first()
    if not director_user:
        seed_all()
        director_user = db.query(User).filter(User.username == "director").first()

    app.dependency_overrides[get_current_user] = lambda: director_user
    client = TestClient(app)

    # Step A: Create a draft PO
    payload = {"supplier_id": 1, "items": [{"sku": "SKU-101", "quantity": 1000}]}

    print("\n1. Creating draft purchase order...")
    resp_create = client.post("/api/enterprise/purchase-orders/create", json=payload)
    if resp_create.status_code != 200:
        print("PO Draft Creation Failed:", resp_create.text)
        db.close()
        sys.exit(1)

    po_data = resp_create.json()
    po_id = po_data["po_id"]
    print(
        f"Draft created successfully. PO ID: {po_id}, Status: {po_data.get('status')}"
    )

    # Step B: Submit the PO
    print(f"\n2. Submitting PO {po_id}...")
    resp_submit = client.post(f"/api/enterprise/purchase-orders/{po_id}/submit")
    if resp_submit.status_code != 200:
        print("PO Submission Failed:", resp_submit.text)
        db.close()
        sys.exit(1)
    print("PO Submitted. Status:", resp_submit.json().get("status"))

    # Step C: Approve the PO
    print(f"\n3. Approving PO {po_id}...")
    resp_approve = client.post(f"/api/enterprise/purchase-orders/{po_id}/approve")
    if resp_approve.status_code != 200:
        print("PO Approval Failed:", resp_approve.text)
        db.close()
        sys.exit(1)
    print("PO Approved. Status:", resp_approve.json().get("status"))

    # Step D: Simulate session refresh & restart backend (Close DB and reopen session)
    print("\n4. Simulating backend/database session restart...")
    db.close()

    # Create a brand new database connection session to query the record
    new_db = SessionLocal()
    po_db = new_db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    if po_db:
        print("\nVerification: Record found in database after session restart.")
        po_record = {
            "id": po_db.id,
            "supplier_id": po_db.supplier_id,
            "status": po_db.status,
            "total_cost": float(po_db.total_cost),
            "details": po_db.details,
            "created_at": po_db.created_at.isoformat(),
        }
        print("Raw Database Record:")
        print(json.dumps(po_record, indent=2))

        if (
            po_db.status == "Approved"
            and len(po_db.details) == 1
            and po_db.details[0]["sku"] == "SKU-101"
        ):
            print("\n[RESULT] PASS")
        else:
            print("\n[RESULT] FAIL - Invalid status or details.")
            new_db.close()
            sys.exit(1)
    else:
        print("\n[RESULT] FAIL - Record not found after session restart.")
        new_db.close()
        sys.exit(1)

    new_db.close()
    app.dependency_overrides.clear()


if __name__ == "__main__":
    test_po_lifecycle()

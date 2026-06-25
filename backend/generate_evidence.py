import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / "backend"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

from backend.database.models import (
    Forecast,
    InventoryItem,
    InventoryTransfer,
    Product,
    Sale,
    Warehouse,
)
from backend.database.session import SessionLocal

# Configuration
API_URL = "http://localhost:8000/api"
ENTERPRISE_API_URL = "http://localhost:8000/api/enterprise"


def run_verification():
    db = SessionLocal()
    print("=== Running Verification Scenarios ===")

    results = {}

    # 1. User Authentication and Tokens
    print("\n[1] Fetching JWT Tokens for RBAC testing...")
    tokens = {}
    roles = ["admin", "director", "manager", "planner"]
    for role in roles:
        try:
            resp = httpx.post(
                f"{API_URL}/auth/login",
                data={"username": role, "password": f"{role}123"},
            )
            if resp.status_code == 200:
                tokens[role] = resp.json()["access_token"]
                print(f"  Token retrieved for '{role}' successfully.")
            else:
                print(
                    f"  Failed to get token for '{role}': {resp.status_code} - {resp.text}"
                )
        except Exception as e:
            print(f"  Error authenticating as '{role}': {e}")

    results["tokens"] = {r: (t[:20] + "..." if t else None) for r, t in tokens.items()}

    # 2. Inventory Transfer Verification
    print("\n[2] Executing Inventory Transfer for SKU-205...")
    sku = "SKU-205"
    wh_from_name = "Warehouse B"
    wh_to_name = "Warehouse A"
    qty_to_transfer = 20.0

    # Check inventory before transfer
    prod = db.query(Product).filter(Product.sku == sku).first()
    w_from = db.query(Warehouse).filter(Warehouse.name == wh_from_name).first()
    w_to = db.query(Warehouse).filter(Warehouse.name == wh_to_name).first()

    inv_from_before = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == w_from.id
        )
        .first()
        .current_stock
    )
    inv_to_before = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == w_to.id
        )
        .first()
        .current_stock
    )
    total_before = inv_from_before + inv_to_before

    print("  Stock before transfer:")
    print(f"    {wh_from_name}: {inv_from_before:.1f} units")
    print(f"    {wh_to_name}: {inv_to_before:.1f} units")
    print(f"    Total Combined: {total_before:.1f} units")

    # Run transfer using director token
    headers_dir = {"Authorization": f"Bearer {tokens['director']}"}
    transfer_payload = {
        "from_wh": wh_from_name,
        "to_wh": wh_to_name,
        "sku": sku,
        "quantity": qty_to_transfer,
    }

    transfer_resp = httpx.post(
        f"{ENTERPRISE_API_URL}/transfers", json=transfer_payload, headers=headers_dir
    )
    print(
        f"  POST /transfers response: {transfer_resp.status_code} - {transfer_resp.text}"
    )
    transfer_data = transfer_resp.json()
    transfer_id = transfer_data.get("transfer_id")

    # Check inventory after transfer
    db.expire_all()
    inv_from_after = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == w_from.id
        )
        .first()
        .current_stock
    )
    inv_to_after = (
        db.query(InventoryItem)
        .filter(
            InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == w_to.id
        )
        .first()
        .current_stock
    )
    total_after = inv_from_after + inv_to_after

    print("  Stock after transfer:")
    print(f"    {wh_from_name}: {inv_from_after:.1f} units")
    print(f"    {wh_to_name}: {inv_to_after:.1f} units")
    print(f"    Total Combined: {total_after:.1f} units")

    # Receive transfer
    receive_resp = httpx.post(
        f"{ENTERPRISE_API_URL}/transfers/{transfer_id}/receive", headers=headers_dir
    )
    print(
        f"  POST /transfers/{transfer_id}/receive response: {receive_resp.status_code} - {receive_resp.text}"
    )

    transfer_record = (
        db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    )

    results["transfers"] = {
        "sku": sku,
        "from_warehouse": wh_from_name,
        "to_warehouse": wh_to_name,
        "qty_transferred": qty_to_transfer,
        "stock_before": {
            wh_from_name: inv_from_before,
            wh_to_name: inv_to_before,
            "total": total_before,
        },
        "stock_after": {
            wh_from_name: inv_from_after,
            wh_to_name: inv_to_after,
            "total": total_after,
        },
        "status_after_creation": transfer_data.get("message"),
        "status_after_receiving": transfer_record.status,
        "stock_conserved": total_before == total_after,
    }

    # 3. RBAC Permissions Verification
    print("\n[3] Verifying RBAC Permissions on PO approval...")
    # Create Draft PO
    headers_plan = {"Authorization": f"Bearer {tokens['planner']}"}
    po_payload = {
        "supplier_id": 1,
        "items": [
            {"sku": "SKU-101", "quantity": 2000}
        ],  # total cost = 120,000 (2000 * 60)
    }
    po_create_resp = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/create",
        json=po_payload,
        headers=headers_plan,
    )
    po_create_data = po_create_resp.json()
    po_id = po_create_data["po_id"]
    po_cost = po_create_data["total_cost"]
    print(f"  Created PO-{po_id} with total cost: INR {po_cost:,.2f}")

    rbac_tests = {}

    # Attempt 1: Planner approving PO (should return 403)
    resp_plan = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/{po_id}/approve",
        headers={"Authorization": f"Bearer {tokens['planner']}"},
    )
    print(
        f"    Planner approval status code: {resp_plan.status_code} - Response: {resp_plan.text}"
    )
    rbac_tests["planner"] = {
        "status_code": resp_plan.status_code,
        "body": resp_plan.json() if resp_plan.status_code == 403 else resp_plan.text,
    }

    # Attempt 2: Manager approving PO (cost = 120,000, which exceeds manager limit of 100,000, should return 403)
    resp_mgr = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/{po_id}/approve",
        headers={"Authorization": f"Bearer {tokens['manager']}"},
    )
    print(
        f"    Manager approval status code: {resp_mgr.status_code} - Response: {resp_mgr.text}"
    )
    rbac_tests["manager"] = {
        "status_code": resp_mgr.status_code,
        "body": resp_mgr.json() if resp_mgr.status_code == 403 else resp_mgr.text,
    }

    # Attempt 3: Director approving PO (cost = 120,000, which is <= 500,000 limit, should succeed with 200)
    resp_dir = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/{po_id}/approve",
        headers={"Authorization": f"Bearer {tokens['director']}"},
    )
    print(
        f"    Director approval status code: {resp_dir.status_code} - Response: {resp_dir.text}"
    )
    rbac_tests["director"] = {
        "status_code": resp_dir.status_code,
        "body": resp_dir.json() if resp_dir.status_code == 200 else resp_dir.text,
    }

    # Create another PO that is very high cost (> 500,000)
    po_payload_high = {
        "supplier_id": 1,
        "items": [
            {"sku": "SKU-101", "quantity": 10000}
        ],  # total cost = 600,000 (10000 * 60)
    }
    po_high_resp = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/create",
        json=po_payload_high,
        headers=headers_plan,
    )
    po_high_id = po_high_resp.json()["po_id"]
    po_high_cost = po_high_resp.json()["total_cost"]
    print(f"  Created PO-{po_high_id} with total cost: INR {po_high_cost:,.2f}")

    # Director approves high cost PO (should fail with 403)
    resp_dir_high = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/{po_high_id}/approve",
        headers={"Authorization": f"Bearer {tokens['director']}"},
    )
    print(
        f"    Director high-cost approval status code: {resp_dir_high.status_code} - Response: {resp_dir_high.text}"
    )
    rbac_tests["director_high_cost"] = {
        "status_code": resp_dir_high.status_code,
        "body": (
            resp_dir_high.json()
            if resp_dir_high.status_code == 403
            else resp_dir_high.text
        ),
    }

    # Admin approves high cost PO (should succeed)
    resp_admin_high = httpx.post(
        f"{ENTERPRISE_API_URL}/purchase-orders/{po_high_id}/approve",
        headers={"Authorization": f"Bearer {tokens['admin']}"},
    )
    print(
        f"    Admin high-cost approval status code: {resp_admin_high.status_code} - Response: {resp_admin_high.text}"
    )
    rbac_tests["admin_high_cost"] = {
        "status_code": resp_admin_high.status_code,
        "body": (
            resp_admin_high.json()
            if resp_admin_high.status_code == 200
            else resp_admin_high.text
        ),
    }

    results["rbac"] = rbac_tests

    # 4. Copilot Chat Queries Verification
    print("\n[4] Querying Copilot Chat with specific prompts...")
    copilot_prompts = [
        "What should I order today?",
        "Which SKU will stock out first?",
        "Which supplier is highest risk?",
        "What revenue is at risk?",
    ]
    copilot_results = {}
    for p in copilot_prompts:
        print(f"  Sending prompt: '{p}'")
        resp = httpx.post(
            f"{ENTERPRISE_API_URL}/copilot/chat",
            json={"prompt": p},
            headers={"Authorization": f"Bearer {tokens['planner']}"},
            timeout=45.0,
        )
        print(f"    Response Status: {resp.status_code}")

        # Retrieve context from database via RAG helper
        from backend.copilot.rag import retrieve_relevant_facts

        facts = retrieve_relevant_facts(db, p, top_k=5)

        copilot_results[p] = {
            "retrieved_context": facts,
            "api_response": resp.json() if resp.status_code == 200 else resp.text,
        }

    results["copilot"] = copilot_results

    # 5. Forecasting Engine Verification
    print("\n[5] Fetching Forecasting details for SKU-101...")
    p101 = db.query(Product).filter(Product.sku == "SKU-101").first()
    sales_101 = (
        db.query(Sale)
        .filter(Sale.product_id == p101.id)
        .order_by(Sale.transaction_date.desc())
        .limit(5)
        .all()
    )
    forecasts_101 = (
        db.query(Forecast)
        .filter(Forecast.product_id == p101.id)
        .order_by(Forecast.forecast_date.asc())
        .limit(5)
        .all()
    )

    results["forecasting"] = {
        "sku": "SKU-101",
        "name": p101.name,
        "category": p101.category,
        "model_used": "XGBoost Ensemble",  # Seeded model breakdown
        "historical_sales_sample": [
            {
                "date": str(s.transaction_date.date()),
                "quantity": s.quantity,
                "price": s.price,
            }
            for s in sales_101
        ],
        "forecast_output_sample": [
            {
                "date": str(f.forecast_date.date()),
                "expected_demand": f.expected_demand,
                "confidence": f.forecast_confidence,
            }
            for f in forecasts_101
        ],
    }

    # Save the output to JSON file
    output_path = ROOT / "backend" / "verification_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[SUCCESS] Saved all verification evidence to {output_path}")

    db.close()


if __name__ == "__main__":
    run_verification()

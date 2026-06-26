import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add backend to path
WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
WORKSPACE_ROOT = WORKSPACE_BACKEND.parent
sys.path.insert(0, str(WORKSPACE_BACKEND))
sys.path.insert(0, str(WORKSPACE_ROOT))

from app import app
from auth.dependencies import get_current_user
from database.models import InventoryItem, Product, User, Warehouse
from database.session import SessionLocal
from fastapi.testclient import TestClient


def perform_user_actions(user_id: int, client: TestClient, actions_count: int):
    # The list of exact simultaneous operations requested
    actions = [
        "dashboard",
        "decision_assignment",
        "po_approval",
        "copilot_request",
        "warehouse_transfer",
    ]
    results = []

    for i in range(actions_count):
        action = random.choice(actions)
        t0 = time.perf_counter()
        success = False
        status_code = None
        error_msg = ""

        try:
            if action == "dashboard":
                resp = client.get("/api/enterprise/dashboard")
                status_code = resp.status_code
                if resp.status_code == 200:
                    success = True

            elif action == "decision_assignment":
                resp = client.post(
                    "/api/enterprise/decisions/SKU-101/assign",
                    json={"username": "planner"},
                )
                status_code = resp.status_code
                if resp.status_code == 200:
                    success = True

            elif action == "po_approval":
                # Create PO first, then approve it to ensure lifecycle correctness
                po_resp = client.post(
                    "/api/enterprise/purchase-orders/create",
                    json={
                        "supplier_id": 1,
                        "items": [{"sku": "SKU-101", "quantity": 10}],
                    },
                )
                if po_resp.status_code == 200:
                    po_id = po_resp.json().get("po_id")
                    # Approve the created PO
                    app_resp = client.post(
                        f"/api/enterprise/purchase-orders/{po_id}/approve"
                    )
                    status_code = app_resp.status_code
                    if app_resp.status_code == 200:
                        success = True
                    else:
                        error_msg = f"Approve failed: {app_resp.text}"
                else:
                    status_code = po_resp.status_code
                    error_msg = f"PO Create failed: {po_resp.text}"

            elif action == "copilot_request":
                resp = client.post(
                    "/api/enterprise/copilot/chat", json={"prompt": "hello"}
                )
                status_code = resp.status_code
                if resp.status_code == 200:
                    success = True

            elif action == "warehouse_transfer":
                resp = client.post(
                    "/api/enterprise/transfers",
                    json={
                        "from_wh": "Warehouse A",
                        "to_wh": "Warehouse B",
                        "sku": "SKU-101",
                        "quantity": 1.0,
                    },
                )
                status_code = resp.status_code
                if resp.status_code == 200:
                    success = True
                else:
                    error_msg = f"Transfer failed: {resp.text}"

        except Exception as e:
            error_msg = str(e)

        latency = (time.perf_counter() - t0) * 1000
        results.append(
            {
                "user_id": user_id,
                "action": action,
                "latency_ms": latency,
                "success": success,
                "status_code": status_code,
                "error": error_msg,
            }
        )
        time.sleep(0.02)

    return results


def run_load_test(users_count: int, actions_per_user: int):
    db = SessionLocal()
    print(f"\n--- Running Concurrency Load Test: {users_count} Users ---")

    # Pre-check SKU-101 stock in Warehouse A to ensure transfers succeed
    prod = db.query(Product).filter(Product.sku == "SKU-101").first()
    wh = db.query(Warehouse).filter(Warehouse.name == "Warehouse A").first()
    if prod and wh:
        inv = (
            db.query(InventoryItem)
            .filter(
                InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == wh.id
            )
            .first()
        )
        if not inv:
            inv = InventoryItem(
                product_id=prod.id, warehouse_id=wh.id, current_stock=5000.0
            )
            db.add(inv)
            db.commit()
        elif inv.current_stock < 1000.0:
            inv.current_stock = 5000.0
            db.commit()

    # Bypass authentication as admin
    admin_user = db.query(User).filter(User.username == "admin").first()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)

    all_results = []

    t_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users_count) as executor:
        futures = [
            executor.submit(perform_user_actions, uid, client, actions_per_user)
            for uid in range(1, users_count + 1)
        ]
        for fut in as_completed(futures):
            all_results.extend(fut.result())

    total_duration = (time.perf_counter() - t_start) * 1000

    total_calls = len(all_results)
    success_calls = sum(1 for r in all_results if r["success"])
    failed_calls = total_calls - success_calls
    avg_latency = (
        sum(r["latency_ms"] for r in all_results) / total_calls if total_calls else 0.0
    )
    error_rate = (failed_calls / total_calls) * 100 if total_calls else 0.0

    print(f"Stats for {users_count} Users:")
    print(f" - Total Operations: {total_calls}")
    print(f" - Successful: {success_calls}")
    print(f" - Failed: {failed_calls} (Error Rate: {error_rate:.2f}%)")
    print(f" - Average Latency: {avg_latency:.2f} ms")

    by_action = {}
    for r in all_results:
        act = r["action"]
        if act not in by_action:
            by_action[act] = []
        by_action[act].append(r)

    for act, res_list in by_action.items():
        act_avg = sum(x["latency_ms"] for x in res_list) / len(res_list)
        act_success = sum(1 for x in res_list if x["success"])
        print(
            f"    * Action '{act}': Avg Latency = {act_avg:.2f} ms, Success = {act_success}/{len(res_list)}"
        )

    db.close()
    return failed_calls == 0


def main():
    print("=== STARTING CONCURRENT USER LOAD TESTING ===")

    pass_5 = run_load_test(5, 5)
    pass_10 = run_load_test(10, 5)
    pass_20 = run_load_test(20, 5)

    if pass_5 and pass_10 and pass_20:
        print("\n[RESULT] PASS")
    else:
        print("\n[RESULT] FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()

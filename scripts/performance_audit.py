import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_BACKEND = WORKSPACE_ROOT / "backend"
sys.path.insert(0, str(WORKSPACE_BACKEND))
sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app import app
from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import SessionLocal
from fastapi.testclient import TestClient


def run_performance_audit():
    db = SessionLocal()
    print("=== PERFORMANCE LATENCY AUDIT ===")

    # 1. Bypass auth
    admin_user = db.query(User).filter(User.username == "admin").first()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)

    # Measure Dashboard
    t0 = time.perf_counter()
    resp_dash = client.get("/api/enterprise/dashboard")
    dash_time = (time.perf_counter() - t0) * 1000
    print(f"Dashboard Load Time: {dash_time:.2f} ms (Status: {resp_dash.status_code})")

    # Measure Warehouse
    t0 = time.perf_counter()
    resp_wh = client.get("/api/enterprise/warehouses")
    wh_time = (time.perf_counter() - t0) * 1000
    print(
        f"Warehouse Network Load Time: {wh_time:.2f} ms (Status: {resp_wh.status_code})"
    )

    # Measure Copilot (rule-based fallback path)
    t0 = time.perf_counter()
    resp_cop = client.post(
        "/api/enterprise/copilot/chat", json={"prompt": "what should I order"}
    )
    cop_time = (time.perf_counter() - t0) * 1000
    print(
        f"Copilot Response Time (Fallback): {cop_time:.2f} ms (Status: {resp_cop.status_code})"
    )

    # Create dummy temp file for upload and import test
    csv_content = "date,product_id,category,units_sold,stock_on_hand,unit_cost,unit_price\n2026-06-01,SKU-101,Beverages,100,50000,1.8,3.5\n"
    temp_dir = WORKSPACE_ROOT / "data" / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / "perf_test_temp.csv"
    temp_file.write_text(csv_content)

    t0 = time.perf_counter()
    upload_resp = client.post(
        "/api/dataset/upload",
        files={"file": (temp_file.name, open(temp_file, "rb"), "text/csv")},
    )
    upload_time = (time.perf_counter() - t0) * 1000
    print(
        f"Dataset Upload Time: {upload_time:.2f} ms (Status: {upload_resp.status_code})"
    )

    temp_id = upload_resp.json()["temp_file_id"]
    import_payload = {
        "temp_file_id": temp_id,
        "source_type": "csv",
        "mapping": {
            "sku": "product_id",
            "date": "date",
            "current_stock": "stock_on_hand",
            "revenue": "units_sold",
            "product_name": None,
            "category": "category",
            "unit_cost": "unit_cost",
            "unit_price": "unit_price",
            "warehouse": None,
        },
        "confirm_low_confidence": True,
    }

    t0 = time.perf_counter()
    import_resp = client.post("/api/dataset/import", json=import_payload)
    import_time = (time.perf_counter() - t0) * 1000
    print(
        f"Dataset Import Time (API response): {import_time:.2f} ms (Status: {import_resp.status_code})"
    )

    db.close()


if __name__ == "__main__":
    run_performance_audit()

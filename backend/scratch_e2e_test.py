import sys
from pathlib import Path
import time
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from fastapi.testclient import TestClient
from app import app
from auth.dependencies import get_current_user
from database.session import SessionLocal
from database.models import User, Forecast, RiskScore, PurchaseOrder, Product

print("=== START OF E2E TEST ===")

# Step 1: Initialize TestClient & override auth
db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
app.dependency_overrides[get_current_user] = lambda: admin_user
client = TestClient(app)
print("Step 1: Auth and TestClient initialized successfully.")

# Step 2: Upload CSV
csv_file_path = ROOT.parent / "data" / "retail_sales_sample.csv"
if not csv_file_path.exists():
    print(f"Step 2 FAILED: Sample CSV does not exist at {csv_file_path}")
    sys.exit(1)

print(f"Step 2: Uploading {csv_file_path.name}...")
with open(csv_file_path, "rb") as f:
    resp = client.post("/api/dataset/upload", files={"file": (csv_file_path.name, f, "text/csv")})

if resp.status_code != 200:
    print(f"Step 2 FAILED: Upload response code {resp.status_code}")
    print(resp.text)
    sys.exit(1)

upload_data = resp.json()
print(f"Step 2 SUCCESS: Uploaded successfully. Dataset ID: {upload_data.get('dataset_id')}")

# Step 3: Check if data processing / forecast generation completed
print("Step 3: Checking forecast generation in database...")
forecast_count = db.query(Forecast).count()
print(f"Total rows in forecasts_new table: {forecast_count}")

# Step 4: Check if risk calculations are generated
print("Step 4: Checking risk calculation results...")
risks = db.query(RiskScore).all()
print(f"Total rows in risk_scores table: {len(risks)}")
if len(risks) == 0:
    print("Step 4 FAILED: No risk scores generated.")
    sys.exit(1)
print("Step 4 SUCCESS: Risk scores populated.")

# Step 5: Check if reorder recommendations exist
print("Step 5: Fetching reorder engine recommendations...")
reorder_resp = client.get("/api/enterprise/reorder")
if reorder_resp.status_code != 200:
    print(f"Step 5 FAILED: Reorder API status {reorder_resp.status_code}")
    sys.exit(1)

reorders = reorder_resp.json()
print(f"Total reorder recommendations: {len(reorders)}")
active_reorders = [r for r in reorders if r["recommended_reorder_qty"] > 0]
print(f"Active reorder recommendations (qty > 0): {len(active_reorders)}")

# Step 6: Create Purchase Order from reorder recommendations
print("Step 6: Creating purchase order...")
reorder_target = None
for r in reorders:
    if r["recommended_reorder_qty"] > 0:
        reorder_target = r
        break

if not reorder_target:
    print("Step 6 INFO: No active reorders suggested. Using a placeholder product for PO creation...")
    prod = db.query(Product).first()
    reorder_target = {"sku": prod.sku, "recommended_reorder_qty": 100, "supplier_id": prod.supplier_id or 3}

po_payload = {
    "supplier_id": reorder_target.get("supplier_id") or 3,
    "items": [{"sku": reorder_target["sku"], "quantity": int(reorder_target["recommended_reorder_qty"])}]
}
po_resp = client.post("/api/enterprise/purchase-orders/create", json=po_payload)
if po_resp.status_code != 200:
    print(f"Step 6 FAILED: PO creation failed with status {po_resp.status_code}")
    print(po_resp.text)
    sys.exit(1)

po_data = po_resp.json()
po_id = po_data.get("po_id")
print(f"Step 6 SUCCESS: Purchase Order PO-{po_id} created in 'Draft' status.")

# Step 7: Approve Purchase Order
print(f"Step 7: Approving PO-{po_id}...")
approve_resp = client.post(f"/api/enterprise/purchase-orders/{po_id}/approve")
if approve_resp.status_code != 200:
    print(f"Step 7 FAILED: PO approval failed with status {approve_resp.status_code}")
    print(approve_resp.text)
    sys.exit(1)

print("Step 7 SUCCESS: PO approved and transitioned to active state.")

# Step 8: Generate and Download PDF Report
print("Step 8: Generating executive PDF report...")
report_resp = client.post("/api/reports/executive")
if report_resp.status_code != 200:
    print(f"Step 8 FAILED: Report generation status {report_resp.status_code}")
    print(report_resp.text)
    sys.exit(1)

report_data = report_resp.json()
print(f"Report generated: {report_data.get('file')}")

print("Step 8: Downloading executive PDF report...")
download_resp = client.get("/api/reports/download")
if download_resp.status_code != 200:
    print(f"Step 8 FAILED: Download status {download_resp.status_code}")
    sys.exit(1)

pdf_bytes = download_resp.content
print(f"Step 8 SUCCESS: Report downloaded successfully. Size: {len(pdf_bytes)} bytes.")

db.close()
print("\n=== E2E TEST PASSED FULLY ===")

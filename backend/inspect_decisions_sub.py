import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient

from app import app
from database.models import User
from database.session import SessionLocal

client = TestClient(app)

# Login/Register
register_payload = {
    "email": "test_enterprise_diag2@retailgpt.com",
    "username": "diag_user2",
    "full_name": "Diag User 2",
    "password": "testpassword123",
    "role": "admin",
}

db = SessionLocal()
existing = db.query(User).filter(User.username == "diag_user2").first()
if existing:
    db.delete(existing)
    db.commit()
db.close()

client.post("/api/auth/register", json=register_payload)

login_payload = {"username": "diag_user2", "password": "testpassword123"}
response = client.post("/api/auth/login", data=login_payload)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get a SKU
resp = client.get("/api/enterprise/decisions", headers=headers)
decisions = resp.json()
if not decisions:
    print("No decisions in database. Seeding must have failed or is empty.")
    sys.exit(1)

sku = decisions[0]["sku"]
print(f"Testing sub-endpoints for SKU: {sku}...")

# 1. Assign
assign_resp = client.post(
    f"/api/enterprise/decisions/{sku}/assign",
    json={"username": "diag_user2"},
    headers=headers,
)
print("Assign Status:", assign_resp.status_code, assign_resp.json())

# 2. Status
status_resp = client.post(
    f"/api/enterprise/decisions/{sku}/status",
    json={"status": "In Progress"},
    headers=headers,
)
print("Status Update:", status_resp.status_code, status_resp.json())

# 3. Notes
notes_resp = client.post(
    f"/api/enterprise/decisions/{sku}/notes",
    json={"note": "Test diagnostic comment"},
    headers=headers,
)
print("Notes Update:", notes_resp.status_code, notes_resp.json())

# 4. Quantity
qty_resp = client.post(
    f"/api/enterprise/decisions/{sku}/quantity",
    json={"quantity": 500.0},
    headers=headers,
)
print("Quantity Update Status:", qty_resp.status_code)
if qty_resp.status_code == 200:
    print(
        "Quantity Update Response:", qty_resp.json()[:1]
    )  # Print first item of returned list
else:
    print("Quantity Update Error:", qty_resp.text)

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient

from app import app
from database.models import User
from database.session import SessionLocal

client = TestClient(app)

# Login
register_payload = {
    "email": "test_enterprise_diag@retailgpt.com",
    "username": "diag_user",
    "full_name": "Diag User",
    "password": "testpassword123",
    "role": "admin",
}

# Clean up existing test user
db = SessionLocal()
existing = db.query(User).filter(User.username == "diag_user").first()
if existing:
    db.delete(existing)
    db.commit()
db.close()

client.post("/api/auth/register", json=register_payload)

login_payload = {"username": "diag_user", "password": "testpassword123"}
response = client.post("/api/auth/login", data=login_payload)
token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("Querying /api/enterprise/decisions...")
resp = client.get("/api/enterprise/decisions", headers=headers)
print("Status Code:", resp.status_code)
if resp.status_code != 200:
    print("Response Content:", resp.text)
else:
    print("Success. Total items:", len(resp.json()))

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient

from app import app
from backend.database.models import User
from backend.database.session import SessionLocal

client = TestClient(app)

# Login/Register Admin
admin_payload = {
    "email": "admin_audit@retailgpt.com",
    "username": "admin_audit",
    "full_name": "Admin Audit",
    "password": "testpassword123",
    "role": "admin",
}

db = SessionLocal()
# Clean up existing test users
for u in ["admin_audit", "new_manager_audit"]:
    existing = db.query(User).filter(User.username == u).first()
    if existing:
        db.delete(existing)
db.commit()
db.close()

# Register Admin
client.post("/api/auth/register", json=admin_payload)
login_resp = client.post(
    "/api/auth/login", data={"username": "admin_audit", "password": "testpassword123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 1. Create a User (Role: Manager)
new_user_payload = {
    "email": "manager_audit@retailgpt.com",
    "username": "new_manager_audit",
    "full_name": "Audit Manager",
    "password": "managerpassword123",
    "role": "manager",
}
print("Registering manager...")
reg_resp = client.post("/api/auth/register", json=new_user_payload)
print("Register Status:", reg_resp.status_code)
print("Register Response:", reg_resp.json())

# 2. List Users
print("\nListing all users in directory...")
list_resp = client.get("/api/auth/users", headers=headers)
print("List Status:", list_resp.status_code)
print("List Response:")
print(json.dumps(list_resp.json(), indent=2))

# 3. Database Confirmation
print("\nDirect Database Confirmation:")
db = SessionLocal()
db_user = db.query(User).filter(User.username == "new_manager_audit").first()
if db_user:
    print("User Found in SQLite DB:")
    print(f"  ID: {db_user.id}")
    print(f"  Username: {db_user.username}")
    print(f"  Email: {db_user.email}")
    print(f"  Role: {db_user.role}")
    print(f"  Active Status: {db_user.is_active}")
else:
    print("Error: User not found in database.")
db.close()

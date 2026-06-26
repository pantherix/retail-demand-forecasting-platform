import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastapi.testclient import TestClient

from app import app
from database.models import User
from database.session import SessionLocal

client = TestClient(app)

# Login/Register
payload = {
    "email": "test_copilot@retailgpt.com",
    "username": "copilot_user",
    "full_name": "Copilot User",
    "password": "testpassword123",
    "role": "admin",
}

db = SessionLocal()
existing = db.query(User).filter(User.username == "copilot_user").first()
if existing:
    db.delete(existing)
    db.commit()
db.close()

client.post("/api/auth/register", json=payload)
login_resp = client.post(
    "/api/auth/login", data={"username": "copilot_user", "password": "testpassword123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

prompts = [
    "Hello, who are you?",
    "What should I order today?",
    "Show details for SKU SKU-101",
    "Which warehouse is overloaded?",
    "Give me reorder recommendations",
]

print("Starting Copilot Queries...")
for p in prompts:
    print(f"\nPrompt: '{p}'")
    resp = client.post(
        "/api/enterprise/copilot/chat", json={"prompt": p}, headers=headers
    )
    print("Status Code:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Answer:")
        print(data.get("answer") or data.get("insight") or json.dumps(data, indent=2))
    else:
        print("Error:", resp.text)

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from fastapi.testclient import TestClient
from app import app
from auth.dependencies import get_current_user
from database.session import SessionLocal
from database.models import User

db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
app.dependency_overrides[get_current_user] = lambda: admin_user
client = TestClient(app)

questions = [
    "Which SKU has highest revenue risk?",
    "Which supplier is causing the biggest problem?",
    "What should I order today?",
    "Which warehouse needs inventory transfer?",
    "What is my biggest operational risk?"
]

results = []
for q in questions:
    resp = client.post("/api/enterprise/copilot/chat", json={"prompt": q})
    results.append({
        "question": q,
        "response": resp.json()
    })

output_path = Path(__file__).resolve().parent / "copilot_audit_output.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Saved Copilot Audit outputs to {output_path}")

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
if not admin_user:
    from database.seed_db import seed_all
    seed_all()
    admin_user = db.query(User).filter(User.username == "admin").first()

app.dependency_overrides[get_current_user] = lambda: admin_user
client = TestClient(app)

results = {}

# 1. AI Copilot Questions
prompts = [
    "Which SKU has highest revenue risk?",
    "What should I reorder today?",
    "Which warehouse needs inventory transfer?",
    "What is my biggest business problem?"
]
copilot_results = []
for p in prompts:
    try:
        resp = client.post("/api/enterprise/copilot/chat", json={"prompt": p})
        copilot_results.append({
            "prompt": p,
            "status": resp.status_code,
            "response": resp.json()
        })
    except Exception as e:
        copilot_results.append({
            "prompt": p,
            "error": str(e)
        })
results["copilot"] = copilot_results

# 2. Executive Briefing
try:
    resp = client.get("/api/enterprise/dashboard")
    results["executive_briefing"] = {
        "status": resp.status_code,
        "response": resp.json()
    }
except Exception as e:
    results["executive_briefing"] = {"error": str(e)}

# 3. Action Center
try:
    resp = client.get("/api/enterprise/decisions")
    results["action_center"] = {
        "status": resp.status_code,
        "response": resp.json()
    }
except Exception as e:
    results["action_center"] = {"error": str(e)}

# 4. Scenario Lab
try:
    resp = client.post("/api/simulation/run-scenario", json={
        "demand_change_pct": 25.0,
        "lead_time_change_days": 3,
        "supplier_reliability_change_pct": -5.0
    })
    results["scenario_lab"] = {
        "status": resp.status_code,
        "response": resp.json()
    }
except Exception as e:
    results["scenario_lab"] = {"error": str(e)}

# 5. Purchase Orders
try:
    resp = client.get("/api/enterprise/purchase-orders")
    results["purchase_orders"] = {
        "status": resp.status_code,
        "response": resp.json()
    }
except Exception as e:
    results["purchase_orders"] = {"error": str(e)}

# 6. Reorder Engine Recommendations
try:
    resp = client.get("/api/enterprise/reorder")
    results["reorder_engine"] = {
        "status": resp.status_code,
        "response": resp.json()
    }
except Exception as e:
    results["reorder_engine"] = {"error": str(e)}

# Save to file
output_path = Path(__file__).resolve().parent / "scratch_output.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"SUCCESS: Saved output to {output_path}")

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from database.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

tables = [
    "products",
    "inventory",
    "forecasts_new",
    "risk_scores",
    "suppliers",
    "warehouses",
    "purchase_orders",
    "alerts",
    "audit_logs"
]

print("=== DATABASE TABLE COUNTS ===")
for t in tables:
    try:
        count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"Table Name: {t} | Row Count: {count}")
    except Exception as e:
        print(f"Table Name: {t} | Error: {e}")

print("\n--- Additional Tables Check ---")
for t in ["users", "roles", "sales", "datasets", "forecasts", "training_runs", "simulation_runs", "reports", "transfers"]:
    try:
        count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"Table Name: {t} | Row Count: {count}")
    except Exception as e:
        print(f"Table Name: {t} | Error: {e}")

db.close()

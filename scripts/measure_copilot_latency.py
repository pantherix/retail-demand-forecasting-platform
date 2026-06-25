import sys
import time
from pathlib import Path

WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
sys.path.insert(0, str(WORKSPACE_BACKEND))

from backend.app import app
from backend.auth.dependencies import get_current_user
from backend.database.models import User
from backend.database.session import SessionLocal
from fastapi.testclient import TestClient


def measure_copilot_latency():
    db = SessionLocal()
    print("=== COPILOT LATENCY AFTER TIMEOUT FIX ===")

    # 1. Bypass auth
    admin_user = db.query(User).filter(User.username == "admin").first()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    client = TestClient(app)

    prompts = ["hello", "how", "help", "warehouse status", "what should I order"]

    total_time = 0
    all_under_3s = True

    for p in prompts:
        t0 = time.perf_counter()
        resp = client.post("/api/enterprise/copilot/chat", json={"prompt": p})
        duration = (time.perf_counter() - t0) * 1000
        total_time += duration

        print(f"Prompt: '{p}'")
        print(f" - Duration: {duration:.2f} ms")
        print(f" - Status Code: {resp.status_code}")

        if duration > 3000:
            print("   [WARNING] Exceeded 3 seconds threshold!")
            all_under_3s = False
        else:
            print("   [OK] Under 3 seconds")

    avg_time = total_time / len(prompts)
    print(f"\nAverage Response Time: {avg_time:.2f} ms")

    if all_under_3s:
        print("\n[RESULT] PASS")
    else:
        print("\n[RESULT] FAIL")
        sys.exit(1)

    db.close()


if __name__ == "__main__":
    measure_copilot_latency()

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


def run_refreshes_benchmark():
    db = SessionLocal()
    print("=== DASHBOARD REFRESH STRESS TEST (50 REFRESHES) ===")

    # 1. Bypass auth as planner
    planner_user = db.query(User).filter(User.username == "planner").first()
    app.dependency_overrides[get_current_user] = lambda: planner_user
    client = TestClient(app)

    latencies = []
    failures = 0

    print("Sending 50 consecutive GET /api/enterprise/dashboard requests...\n")
    for i in range(1, 51):
        t0 = time.perf_counter()
        try:
            resp = client.get("/api/enterprise/dashboard")
            duration = (time.perf_counter() - t0) * 1000
            latencies.append(duration)

            if resp.status_code == 200:
                print(f"Request {i:02d}: Status 200 | Latency: {duration:.2f} ms")
            else:
                print(
                    f"Request {i:02d}: Status {resp.status_code} [FAIL] | Latency: {duration:.2f} ms"
                )
                failures += 1
        except Exception as e:
            duration = (time.perf_counter() - t0) * 1000
            print(
                f"Request {i:02d}: Exception - {e} [FAIL] | Latency: {duration:.2f} ms"
            )
            failures += 1

    avg_time = sum(latencies) / len(latencies) if latencies else 0.0
    print("\nSTRESS TEST SUMMARY:")
    print("Total Requests: 50")
    print(f"Successful Requests: {50 - failures}/50")
    print(f"Failed Requests: {failures}")
    print(f"Average Response Time: {avg_time:.2f} ms")

    if failures == 0:
        print("\n[RESULT] PASS")
    else:
        print("\n[RESULT] FAIL")
        db.close()
        sys.exit(1)

    db.close()


if __name__ == "__main__":
    run_refreshes_benchmark()

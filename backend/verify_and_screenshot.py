import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Generate JWT Token for Admin
sys.path.append(str(ROOT / "backend"))
from auth.security import create_access_token
from database.models import User
from database.session import SessionLocal

# Verify database tables and seed exist
db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
if not admin_user:
    from database.seed_db import seed_all

    seed_all()
    admin_user = db.query(User).filter(User.username == "admin").first()

token = create_access_token(data={"sub": "admin"})
db.close()


def run_screenshot_capture():
    print("Starting backend server on http://localhost:8000...", flush=True)
    backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT / "backend",
    )

    print("Starting Next.js frontend server on http://localhost:3000...", flush=True)
    frontend_proc = subprocess.Popen(
        "npx next dev --port 3000", shell=True, cwd=ROOT / "frontend"
    )

    # Wait for servers to respond
    print("Waiting for servers to be ready...", flush=True)
    servers_ready = False
    for attempt in range(30):
        try:
            req_back = urllib.request.Request("http://127.0.0.1:8000/health")
            with urllib.request.urlopen(req_back, timeout=1.0) as r:
                back_ok = r.status == 200

            req_front = urllib.request.Request("http://localhost:3000")
            with urllib.request.urlopen(req_front, timeout=1.0) as r:
                front_ok = r.status == 200

            if back_ok and front_ok:
                servers_ready = True
                print("Both servers respond with status code 200!", flush=True)
                break
        except Exception:
            pass
        time.sleep(2.0)

    if not servers_ready:
        print("Error: Servers failed to start in time. Aborting.", flush=True)
        backend_proc.terminate()
        frontend_proc.terminate()
        return

    # Define all 9 views to capture in executive dark theme
    pages = [
        {
            "name": "Command_Brief",
            "url": f"http://localhost:3000/?token={token}&tab=executive&theme=dark",
        },
        {
            "name": "Decision_Center",
            "url": f"http://localhost:3000/?token={token}&tab=action-center&theme=dark",
        },
        {
            "name": "Scenario_Lab",
            "url": f"http://localhost:3000/?token={token}&tab=scenario-lab&theme=dark",
        },
        {
            "name": "Reorder_Engine",
            "url": f"http://localhost:3000/?token={token}&tab=reorder&theme=dark",
        },
        {
            "name": "Decision_Copilot",
            "url": f"http://localhost:3000/?token={token}&tab=copilot&theme=dark",
        },
        {
            "name": "Warehouse_Network",
            "url": f"http://localhost:3000/?token={token}&tab=warehouses&theme=dark",
        },
        {
            "name": "PO_Automation",
            "url": f"http://localhost:3000/?token={token}&tab=purchase-orders&theme=dark",
        },
        {
            "name": "Data_Upload",
            "url": f"http://localhost:3000/?token={token}&tab=datasets&theme=dark",
        },
        {
            "name": "User_Management",
            "url": f"http://localhost:3000/?token={token}&tab=users&theme=dark",
        },
    ]

    artifacts_dir = Path(
        r"C:\Users\statu\.gemini\antigravity-ide\brain\bc0fafb5-94cb-4a80-b959-e5fdde2df8ac"
    )
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    for p in pages:
        save_file = artifacts_dir / f"{p['name']}.png"
        print(f"Capturing: {p['name']}...", flush=True)

        chrome_args = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1280,1024",
            f"--screenshot={save_file}",
            p["url"],
        ]

        chrome_proc = subprocess.run(chrome_args, capture_output=True, timeout=30.0)
        print(f"Saved: {save_file}. Code: {chrome_proc.returncode}", flush=True)
        time.sleep(3.0)

    print("Cleaning up server processes...", flush=True)
    backend_proc.terminate()
    backend_proc.wait()
    subprocess.run("taskkill /F /IM node.exe", shell=True, capture_output=True)
    subprocess.run("taskkill /F /IM uvicorn.exe", shell=True, capture_output=True)
    print("Screenshot process finished successfully!", flush=True)


if __name__ == "__main__":
    run_screenshot_capture()

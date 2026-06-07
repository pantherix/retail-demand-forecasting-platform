import sys
import os
import time
import subprocess
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parent.parent

# Generate JWT Token for Admin
from database.session import SessionLocal
from database.models import User
from auth.security import create_access_token

db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
if not admin_user:
    from database.seed_db import seed_all
    seed_all()
    admin_user = db.query(User).filter(User.username == "admin").first()

token = create_access_token(data={"sub": "admin"})
db.close()

def run_screenshot_capture():
    print("Starting backend server...", flush=True)
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT / "backend"
    )

    print("Starting frontend server...", flush=True)
    frontend_proc = subprocess.Popen(
        "npx next dev --port 3000",
        shell=True,
        cwd=ROOT / "frontend"
    )

    # Wait for servers to be active
    print("Waiting for servers to respond...", flush=True)
    servers_ready = False
    for attempt in range(30):
        try:
            r_back = httpx.get("http://127.0.0.1:8000/health", timeout=1.0)
            r_front = httpx.get("http://localhost:3000", timeout=1.0)
            if r_back.status_code == 200 and r_front.status_code == 200:
                servers_ready = True
                print("Both servers are up and running!", flush=True)
                break
        except Exception:
            pass
        time.sleep(2.0)

    if not servers_ready:
        print("Error: Servers failed to start in time.", flush=True)
        backend_proc.terminate()
        frontend_proc.terminate()
        return

    # Capture screenshots for every page tab
    pages_to_test = [
        {"name": "1_command_brief", "tab": "executive"},
        {"name": "2_decision_center", "tab": "action-center"},
        {"name": "3_scenario_lab", "tab": "scenario-lab"},
        {"name": "4_reorder_engine", "tab": "reorder"},
        {"name": "5_decision_copilot", "tab": "copilot"},
        {"name": "6_warehouse_network", "tab": "warehouses"},
        {"name": "7_po_automation", "tab": "purchase-orders"}
    ]

    artifacts_dir = Path(r"C:\Users\statu\.gemini\antigravity\brain\b04255f2-5a7c-4287-8868-7d615ff8ed2d")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    for p in pages_to_test:
        save_file = artifacts_dir / f"{p['name']}.png"
        url = f"http://localhost:3000/?token={token}&tab={p['tab']}"
        print(f"Capturing screenshot for {p['name']} via URL: {url}...", flush=True)
        
        # Chrome command line screenshot capture
        chrome_args = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1280,1024",
            "--virtual-time-budget=5000",
            f"--screenshot={save_file}",
            url
        ]
        
        # Run Chrome and wait for exit
        chrome_proc = subprocess.run(chrome_args, capture_output=True, timeout=20.0)
        print(f"Saved screenshot: {save_file}. Code: {chrome_proc.returncode}", flush=True)
        time.sleep(2.0)

    print("Cleaning up server processes...", flush=True)
    backend_proc.terminate()
    subprocess.run("taskkill /F /IM node.exe", shell=True)
    subprocess.run("taskkill /F /IM uvicorn.exe", shell=True)
    print("Screenshot process complete!", flush=True)

if __name__ == "__main__":
    run_screenshot_capture()

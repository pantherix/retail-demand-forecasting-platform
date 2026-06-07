import sys
import os
import time
import subprocess
import json
import asyncio
from pathlib import Path
import httpx
import websockets

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

async def run_screenshot_capture():
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

    # Start Chrome Headless with Remote Debugging
    print("Launching Chrome in headless mode with remote debugging...", flush=True)
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    chrome_profile = ROOT / "chrome_profile"
    
    # Delete old lock file to prevent locking issues
    lock_file = chrome_profile / "SingletonLock"
    if lock_file.exists():
        try:
            lock_file.unlink()
        except Exception:
            pass

    chrome_proc = subprocess.Popen([
        chrome_path,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--remote-debugging-port=9222",
        f"--user-data-dir={chrome_profile}"
    ])

    # Wait for Chrome debug port
    time.sleep(4.0)

    # Get WebSocket debugger URL
    print("Querying Chrome for debugger URL...", flush=True)
    try:
        r_debug = httpx.get("http://127.0.0.1:9222/json/list")
        tabs = r_debug.json()
        target_ws_url = None
        for tab in tabs:
            if tab.get("type") == "page":
                target_ws_url = tab.get("webSocketDebuggerUrl")
                break
        
        # If no page tab is active, open a new target page
        if not target_ws_url:
            r_new = httpx.put("http://127.0.0.1:9222/json/new?http://localhost:3000")
            target_ws_url = r_new.json().get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"Failed to query Chrome DevTools: {e}", flush=True)
        chrome_proc.terminate()
        backend_proc.terminate()
        frontend_proc.terminate()
        return

    print(f"Connecting to Chrome WebSocket debugger: {target_ws_url}", flush=True)
    async with websockets.connect(target_ws_url) as ws:
        async def call_cdp(method, params=None):
            msg_id = int(time.time() * 1000)
            payload = {"id": msg_id, "method": method, "params": params or {}}
            await ws.send(json.dumps(payload))
            while True:
                resp = await ws.recv()
                data = json.loads(resp)
                if data.get("id") == msg_id:
                    return data.get("result")

        # Enable Page Domain
        await call_cdp("Page.enable")
        await call_cdp("Runtime.enable")

        # Navigate to localhost:3000
        print("Navigating to http://localhost:3000...", flush=True)
        await call_cdp("Page.navigate", {"url": "http://localhost:3000"})
        await asyncio.sleep(6.0)

        # Inject LocalStorage Auth Token & reload page
        print("Injecting authentication token into localStorage...", flush=True)
        inject_js = f"""
        localStorage.setItem("token", "{token}");
        localStorage.setItem("username", "admin");
        localStorage.setItem("role", "admin");
        localStorage.setItem("full_name", "Executive Admin");
        location.reload();
        """
        await call_cdp("Runtime.evaluate", {"expression": inject_js})
        await asyncio.sleep(8.0) # Wait for reload and data sync fetch calls

        # Capture screenshots for every page tab
        pages_to_test = [
            {"name": "1_command_brief", "btn_text": "Command Brief"},
            {"name": "2_decision_center", "btn_text": "Decision Center"},
            {"name": "3_scenario_lab", "btn_text": "Scenario Lab"},
            {"name": "4_reorder_engine", "btn_text": "Reorder Engine"},
            {"name": "5_decision_copilot", "btn_text": "Decision Copilot"},
            {"name": "6_warehouse_network", "btn_text": "Warehouse Network"},
            {"name": "7_po_automation", "btn_text": "PO Automation"}
        ]

        artifacts_dir = Path(r"C:\Users\statu\.gemini\antigravity\brain\b04255f2-5a7c-4287-8868-7d615ff8ed2d")
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        for p in pages_to_test:
            print(f"Switching to page: {p['btn_text']}...", flush=True)
            click_js = f"""
            (() => {{
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.includes("{p['btn_text']}"));
                if (btn) {{
                    btn.click();
                    return true;
                }}
                return false;
            }})()
            """
            eval_res = await call_cdp("Runtime.evaluate", {"expression": click_js})
            print(f"Click result for {p['btn_text']}: {eval_res}", flush=True)
            
            # Wait for data load/render animations
            await asyncio.sleep(5.0)

            # Capture Screenshot
            print(f"Capturing screenshot for {p['name']}...", flush=True)
            screenshot_data = await call_cdp("Page.captureScreenshot", {"format": "png"})
            import base64
            img_bytes = base64.b64decode(screenshot_data.get("data"))
            
            save_file = artifacts_dir / f"{p['name']}.png"
            save_file.write_bytes(img_bytes)
            print(f"Saved screenshot to {save_file}", flush=True)

    print("Cleaning up Chrome and server processes...", flush=True)
    chrome_proc.terminate()
    backend_proc.terminate()
    subprocess.run("taskkill /F /IM node.exe", shell=True)
    subprocess.run("taskkill /F /IM uvicorn.exe", shell=True)
    print("Screenshot process complete!", flush=True)

if __name__ == "__main__":
    asyncio.run(run_screenshot_capture())

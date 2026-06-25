import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Generate JWT Token for Admin
sys.path.append(str(ROOT / "backend"))
from backend.auth.security import create_access_token
from backend.database.models import User
from backend.database.session import SessionLocal

db = SessionLocal()
admin_user = db.query(User).filter(User.username == "admin").first()
if not admin_user:
    from backend.database.seed_db import seed_all

    seed_all()
    admin_user = db.query(User).filter(User.username == "admin").first()

token = create_access_token(data={"sub": "admin"})
db.close()


def capture_screenshots():
    pages_to_screenshot = [
        {"name": "Registration", "url": "http://localhost:3000/?register=true"},
        {
            "name": "User_Management",
            "url": f"http://localhost:3000/?token={token}&tab=users",
        },
        {
            "name": "Dataset_Upload",
            "url": f"http://localhost:3000/?token={token}&tab=datasets",
        },
        {
            "name": "Dashboard_PDF_Export",
            "url": f"http://localhost:3000/?token={token}&tab=executive",
        },
        {
            "name": "Warehouse_Empty_State",
            "url": f"http://localhost:3000/?token={token}&tab=warehouses",
        },
    ]

    artifacts_dir = Path(
        r"C:\Users\statu\.gemini\antigravity-ide\brain\bc0fafb5-94cb-4a80-b959-e5fdde2df8ac"
    )
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    workspace_dir = Path(
        r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\artifacts"
    )
    workspace_dir.mkdir(parents=True, exist_ok=True)

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    for p in pages_to_screenshot:
        save_file = artifacts_dir / f"{p['name']}.png"
        print(
            f"Capturing screenshot for {p['name']} via URL: {p['url']}...", flush=True
        )

        # Chrome command line screenshot capture
        chrome_args = [
            chrome_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--window-size=1280,1024",
            "--virtual-time-budget=6000",
            f"--screenshot={save_file}",
            p["url"],
        ]

        # Run Chrome and wait for exit
        chrome_proc = subprocess.run(chrome_args, capture_output=True, timeout=25.0)
        print(
            f"Saved to brain: {save_file}. Code: {chrome_proc.returncode}", flush=True
        )

        # Copy to workspace artifacts too
        try:
            workspace_file = workspace_dir / f"{p['name']}.png"
            shutil.copy2(save_file, workspace_file)
            print(f"Copied to workspace: {workspace_file}", flush=True)
        except Exception as e:
            print(f"Copy failed: {e}", flush=True)

        time.sleep(2.0)

    print("Screenshot process complete!", flush=True)


if __name__ == "__main__":
    capture_screenshots()

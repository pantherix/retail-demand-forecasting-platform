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
    "email": "test_pdf@retailgpt.com",
    "username": "pdf_user",
    "full_name": "PDF User",
    "password": "testpassword123",
    "role": "admin",
}

db = SessionLocal()
existing = db.query(User).filter(User.username == "pdf_user").first()
if existing:
    db.delete(existing)
    db.commit()
db.close()

client.post("/api/auth/register", json=payload)
login_resp = client.post(
    "/api/auth/login", data={"username": "pdf_user", "password": "testpassword123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 1. Generate Executive Report
print("Generating report via POST /api/reports/executive...")
gen_resp = client.post("/api/reports/executive", headers=headers)
print("Gen Status Code:", gen_resp.status_code)
print("Gen Response:", gen_resp.json())

# 2. Download Report
print("\nDownloading report via GET /api/reports/download...")
dl_resp = client.get("/api/reports/download", headers=headers)
print("DL Status Code:", dl_resp.status_code)
if dl_resp.status_code == 200:
    content = dl_resp.content
    size_bytes = len(content)
    print("Download Succeeded!")
    print(f"  Downloaded Content Size: {size_bytes / 1024:.2f} KB ({size_bytes} bytes)")

    # Save a copy to verified path
    out_path = Path("generated_reports/audit_test_report.pdf")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(content)
    print(f"  Saved report copy to: {out_path.resolve()}")
else:
    print("Download Error:", dl_resp.text)

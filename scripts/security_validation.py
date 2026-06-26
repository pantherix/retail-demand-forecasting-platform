import os
import sys
import time
from pathlib import Path

from jose import jwt

WORKSPACE_BACKEND = Path(
    r"c:\Users\statu\Downloads\my projects\retail-demand-forecasting-platform\backend"
)
sys.path.insert(0, str(WORKSPACE_BACKEND))

from app import app
from auth.security import create_access_token
from database.models import User
from database.session import SessionLocal
from fastapi.testclient import TestClient


def run_security_validation():
    db = SessionLocal()
    print("=== SECURITY AUDIT & PENETRATION VERIFICATION ===")
    client = TestClient(app)

    pass_flag = True

    # 1. JWT Security Controls
    print("\n--- 1. Testing JWT Authorization ---")

    # A. Missing JWT
    resp_missing = client.get("/api/auth/users")
    print(f"Missing JWT: Status = {resp_missing.status_code} (Expected: 401)")
    if resp_missing.status_code != 401:
        pass_flag = False

    # B. Invalid JWT Signature
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTk5OTk5OTk5OX0.invalid-signature"
    resp_invalid = client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {invalid_token}"}
    )
    print(f"Invalid JWT Signature: Status = {resp_invalid.status_code} (Expected: 401)")
    if resp_invalid.status_code != 401:
        pass_flag = False

    # C. Expired JWT
    # Generate a token with a past expiry
    secret_key = os.getenv(
        "SECRET_KEY", "retailgpt-super-secret-key-change-in-production"
    )
    expired_payload = {"sub": "admin", "exp": int(time.time()) - 3600}
    expired_token = jwt.encode(expired_payload, secret_key, algorithm="HS256")
    resp_expired = client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {expired_token}"}
    )
    print(f"Expired JWT: Status = {resp_expired.status_code} (Expected: 401)")
    if resp_expired.status_code != 401:
        pass_flag = False

    # 2. RBAC Permissions Boundary
    print("\n--- 2. Testing RBAC Permissions ---")

    # Planner user token
    planner = db.query(User).filter(User.username == "planner").first()
    planner_token = create_access_token({"sub": planner.username})

    # Non-admin user hitting admin-only /api/auth/users
    resp_rbac = client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {planner_token}"}
    )
    print(
        f"Planner hitting Admin user list: Status = {resp_rbac.status_code} (Expected: 403)"
    )
    if resp_rbac.status_code != 403:
        pass_flag = False

    # 3. Upload Validation Boundaries
    print("\n--- 3. Testing Upload Security ---")
    admin = db.query(User).filter(User.username == "admin").first()
    admin_token = create_access_token({"sub": admin.username})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # A. Invalid extension (.txt/shell script)
    txt_file = ("exploit.sh", b"#!/bin/bash\necho 'hacked'", "text/plain")
    resp_ext = client.post(
        "/api/dataset/upload", files={"file": txt_file}, headers=headers
    )
    print(f"Malicious Extension (.sh): Status = {resp_ext.status_code} (Expected: 400)")
    if resp_ext.status_code != 400:
        pass_flag = False

    # B. Path Traversal Filename
    traversal_file = (
        "../../../../etc/passwd",
        b"date,sku,category,units_sold\n2026-06-01,SKU-101,Beverages,50\n",
        "text/csv",
    )
    resp_traversal = client.post(
        "/api/dataset/upload", files={"file": traversal_file}, headers=headers
    )
    print(f"Path Traversal Filename (../): Status = {resp_traversal.status_code}")
    # The file should be saved under DATA_DIR / sanitized_filename or fail.
    # Let's verify that the backend does not write outside the upload directory!
    temp_file_id = resp_traversal.json().get("temp_file_id", "")
    print(f"Saved Filename ID: {temp_file_id}")
    if "/" in temp_file_id or "\\" in temp_file_id:
        print("   [CRITICAL] Directory traversal vulnerable!")
        pass_flag = False
    else:
        print("   [OK] Path traversal neutralized (filename sanitized).")

    # C. Empty File Upload
    empty_file = ("empty.csv", b"", "text/csv")
    resp_empty = client.post(
        "/api/dataset/upload", files={"file": empty_file}, headers=headers
    )
    print(f"Empty File Upload: Status = {resp_empty.status_code} (Expected: 400)")
    if resp_empty.status_code != 400:
        pass_flag = False

    db.close()

    if pass_flag:
        print("\n[RESULT] PASS")
    else:
        print("\n[RESULT] FAIL")
        sys.exit(1)


if __name__ == "__main__":
    run_security_validation()

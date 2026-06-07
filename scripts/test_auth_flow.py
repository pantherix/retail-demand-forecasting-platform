import requests
import uuid
import sys
from pathlib import Path
import csv

# Configuration
BASE_URL = "http://localhost:8000/api"
UNIQUE_ID = uuid.uuid4().hex[:6]
TEST_USER = {
    "email": f"testuser_{UNIQUE_ID}@retailgpt.com",
    "username": f"user_{UNIQUE_ID}",
    "full_name": "Happy Path Tester",
    "password": "securepassword123",
    "role": "admin"
}

# Create a temporary CSV file path for forecasting tests
ROOT_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = ROOT_DIR / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_CSV_PATH = UPLOADS_DIR / f"test_flow_sales_{UNIQUE_ID}.csv"

def create_temp_sales_data(file_path: Path):
    """Creates a mock historical sales CSV file for training/prediction testing."""
    headers = ["product_id", "date", "sales", "selling_price", "unit_cost"]
    # 60 days of historical sales
    rows = [
        ["SKU-101", f"2026-04-{day:02d}", 10 + (day % 3), 150.0, 60.0]
        for day in range(1, 31)
    ] + [
        ["SKU-101", f"2026-05-{day:02d}", 12 + (day % 4), 150.0, 60.0]
        for day in range(1, 31)
    ]
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Mock sales CSV created at: {file_path}")

def cleanup_temp_sales_data(file_path: Path):
    """Deletes the mock sales CSV file if it exists."""
    if file_path.exists():
        file_path.unlink()
        print(f"Cleaned up mock sales CSV from: {file_path}")

def run_auth_flow_test():
    print("=== START OF INTEGRATED AUTH, DATA & ML PIPELINE smoke test ===")
    
    # Pre-step: Create mock data
    create_temp_sales_data(TEMP_CSV_PATH)
    
    access_token = None
    try:
        # Step 1a: Register User
        print(f"\nStep 1a: Registering new test user: {TEST_USER['username']}...")
        register_url = f"{BASE_URL}/auth/register"
        resp = requests.post(register_url, json=TEST_USER)
        if resp.status_code == 201:
            print(f"SUCCESS: User registered successfully (HTTP {resp.status_code}).")
            print(resp.json())
        elif resp.status_code == 400 and "already" in resp.text:
            print(f"INFO: User already registered (HTTP {resp.status_code}). Proceeding to login...")
        else:
            print(f"FAILED: Registration failed with HTTP {resp.status_code}.")
            print(resp.text)
            sys.exit(1)

        # Step 1b: Login User (Using URL-encoded form data via `data=`)
        print(f"\nStep 1b: Logging in user: {TEST_USER['username']}...")
        login_url = f"{BASE_URL}/auth/login"
        login_payload = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"]
        }
        resp = requests.post(login_url, data=login_payload)
        if resp.status_code == 200:
            token_info = resp.json()
            access_token = token_info.get("access_token")
            print(f"SUCCESS: Login successful (HTTP {resp.status_code}).")
            print(f"Token type: {token_info.get('token_type')}")
            print(f"Captured Token: {access_token[:15]}... [TRUNCATED]")
        else:
            print(f"FAILED: Login failed with HTTP {resp.status_code} (validation error).")
            print(resp.text)
            sys.exit(1)

        # Headers for authenticated requests
        auth_headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # Step 2: Authenticated Profile Check
        print("\nStep 2: Checking authenticated user profile (/auth/me)...")
        me_url = f"{BASE_URL}/auth/me"
        resp = requests.get(me_url, headers=auth_headers)
        if resp.status_code == 200:
            print(f"SUCCESS: Profile loaded successfully (HTTP {resp.status_code}).")
            print(resp.json())
        else:
            print(f"FAILED: Profile check failed with HTTP {resp.status_code}.")
            print(resp.text)
            sys.exit(1)

        # Step 3: Authenticated Data Access
        print("\nStep 3: Checking authenticated dataset access (/dataset/list)...")
        dataset_url = f"{BASE_URL}/dataset/list"
        resp = requests.get(dataset_url, headers=auth_headers)
        if resp.status_code == 200:
            print(f"SUCCESS: Dataset list retrieved successfully (HTTP {resp.status_code}).")
            print(resp.json())
        else:
            print(f"FAILED: Dataset retrieval failed with HTTP {resp.status_code}.")
            print(resp.text)
            sys.exit(1)

        # Step 4: Model Training Pipeline
        print(f"\nStep 4: Training XGBoost forecaster for SKU-101 using temporary CSV...")
        train_url = f"{BASE_URL}/forecast/train"
        train_payload = {
            "sku": "SKU-101",
            "csv_path": str(TEMP_CSV_PATH.resolve())
        }
        resp = requests.post(train_url, json=train_payload, headers=auth_headers)
        if resp.status_code == 200:
            print(f"SUCCESS: Forecasting model trained successfully (HTTP {resp.status_code}).")
            print(resp.json())
        else:
            print(f"FAILED: Model training failed with HTTP {resp.status_code}.")
            print(resp.text)
            sys.exit(1)

        # Step 5: Inference Pipeline (Predict)
        print(f"\nStep 5: Testing 30-day forecast predictions for SKU-101...")
        predict_url = f"{BASE_URL}/forecast/predict"
        predict_payload = {
            "sku": "SKU-101",
            "history_path": str(TEMP_CSV_PATH.resolve()),
            "horizon": 30
        }
        resp = requests.post(predict_url, json=predict_payload, headers=auth_headers)
        if resp.status_code == 200:
            print(f"SUCCESS: Forecast predictions completed successfully (HTTP {resp.status_code}).")
            print(resp.json())
        else:
            print(f"FAILED: Forecasting predictions failed with HTTP {resp.status_code}.")
            print(resp.text)
            sys.exit(1)

        print("\n=== ALL E2E AUTH, DATA & ML TESTS PASSED PERFECTLY ===")

    finally:
        # Cleanup mock data file
        cleanup_temp_sales_data(TEMP_CSV_PATH)

if __name__ == "__main__":
    run_auth_flow_test()

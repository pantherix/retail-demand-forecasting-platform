from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.api.dataset import detect_column_mappings
from backend.app import app

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    register_payload = {
        "email": "regression_tester@retailgpt.com",
        "username": "reg_tester",
        "full_name": "Regression Tester",
        "password": "testpassword123",
        "role": "admin",
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "reg_tester", "password": "testpassword123"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_missing_sku_mapping_blocks_import(auth_headers):
    # Prepare mock CSV data
    df = pd.DataFrame(
        [
            {
                "id": "SKU-999",
                "date": "2026-06-01",
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            }
        ]
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # Upload first
    files = {"file": ("test_upload.csv", csv_bytes, "text/csv")}
    upload_resp = client.post("/api/dataset/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 200
    temp_file_id = upload_resp.json()["temp_file_id"]

    # Import without SKU mapping
    import_payload = {
        "temp_file_id": temp_file_id,
        "source_type": "csv",
        "mapping": {
            "date": "date",
            "current_stock": "qty",
            "unit_price": "price",
            "unit_cost": "cost",
        },
    }
    import_resp = client.post(
        "/api/dataset/import", json=import_payload, headers=auth_headers
    )
    assert import_resp.status_code == 400
    assert "Required target field 'sku' is not mapped" in import_resp.json()["detail"]


def test_missing_date_mapping_blocks_import(auth_headers):
    df = pd.DataFrame(
        [
            {
                "sku": "SKU-999",
                "date": "2026-06-01",
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            }
        ]
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # Upload
    files = {"file": ("test_upload.csv", csv_bytes, "text/csv")}
    upload_resp = client.post("/api/dataset/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 200
    temp_file_id = upload_resp.json()["temp_file_id"]

    # Import without Date mapping
    import_payload = {
        "temp_file_id": temp_file_id,
        "source_type": "csv",
        "mapping": {
            "sku": "sku",
            "current_stock": "qty",
            "unit_price": "price",
            "unit_cost": "cost",
        },
    }
    import_resp = client.post(
        "/api/dataset/import", json=import_payload, headers=auth_headers
    )
    assert import_resp.status_code == 400
    assert "Required target field 'date' is not mapped" in import_resp.json()["detail"]


def test_duplicate_mapping_blocks_import(auth_headers):
    df = pd.DataFrame(
        [
            {
                "sku": "SKU-999",
                "date": "2026-06-01",
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            }
        ]
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # Upload
    files = {"file": ("test_upload.csv", csv_bytes, "text/csv")}
    upload_resp = client.post("/api/dataset/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 200
    temp_file_id = upload_resp.json()["temp_file_id"]

    # Import with duplicate mapping (mapping both sku and date to the same column 'sku')
    import_payload = {
        "temp_file_id": temp_file_id,
        "source_type": "csv",
        "mapping": {"sku": "sku", "date": "sku", "current_stock": "qty"},
    }
    import_resp = client.post(
        "/api/dataset/import", json=import_payload, headers=auth_headers
    )
    assert import_resp.status_code == 400
    assert (
        "Multiple target fields cannot be mapped to the same source column"
        in import_resp.json()["detail"]
    )


def test_skipped_empty_rows(auth_headers):
    # CSV with missing SKU row, missing Date row, and a valid row
    df = pd.DataFrame(
        [
            {
                "sku": "",
                "date": "2026-06-01",
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            },  # empty sku (filtered early by adapter)
            {
                "sku": "SKU-999",
                "date": None,
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            },  # empty date (defaults to utcnow)
            {
                "sku": "SKU-999",
                "date": "2026-06-01",
                "qty": 100,
                "price": 10.0,
                "cost": 5.0,
            },  # valid
        ]
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    files = {"file": ("test_upload.csv", csv_bytes, "text/csv")}
    upload_resp = client.post("/api/dataset/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 200
    temp_file_id = upload_resp.json()["temp_file_id"]

    import_payload = {
        "temp_file_id": temp_file_id,
        "source_type": "csv",
        "mapping": {
            "sku": "sku",
            "date": "date",
            "current_stock": "qty",
            "unit_price": "price",
            "unit_cost": "cost",
        },
    }
    import_resp = client.post(
        "/api/dataset/import", json=import_payload, headers=auth_headers
    )
    assert import_resp.status_code == 200
    data = import_resp.json()
    assert data["success"] is True
    # The early filter skipped the empty sku row.
    # The default logic filled the empty date with utcnow.
    # So 2 rows are imported successfully, and 0 rejected.
    assert data["metrics"]["imported_rows"] == 2
    assert data["metrics"]["rejected_rows"] == 0


def test_transaction_id_mapping_avoidance():
    # Verify that a Transaction ID column is penalized and avoids becoming a SKU automatically
    df = pd.DataFrame(
        [
            {
                "transaction_id": "TXN10001",
                "sku": "SKU-101",
                "date": "2026-06-01",
                "qty": 100,
            }
        ]
    )
    mappings = detect_column_mappings(df)

    sku_mapping = mappings.get("sku", {})
    # Best match should be 'sku', not 'transaction_id'
    assert sku_mapping["best_match"] == "sku"

    # Check that transaction_id has a very low confidence score compared to sku
    candidates = sku_mapping["candidates"]
    txn_candidate = next(
        (x for x in candidates if x["column"] == "transaction_id"), None
    )
    sku_candidate = next((x for x in candidates if x["column"] == "sku"), None)

    assert sku_candidate["confidence"] > 0.8
    # 'transaction_id' is in the avoid list of 'sku', so its confidence is penalized
    assert txn_candidate["confidence"] < 0.2

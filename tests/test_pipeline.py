from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app import app
from backend.database.models import (
    Alert,
    Forecast,
    InventoryItem,
    Product,
    RiskScore,
    Sale,
    User,
)
from backend.database.session import SessionLocal
from backend.forecasting.pipeline import run_training_pipeline

client = TestClient(app)


def test_pipeline_integration():
    # 1. Create a dummy transaction dataset CSV file
    data = []
    start_date = datetime.utcnow() - timedelta(days=60)
    for i in range(60):
        t_date = start_date + timedelta(days=i)
        data.append(
            {
                "product_id": "SKU-TEST-999",
                "date": t_date.strftime("%Y-%m-%d"),
                "quantity": 12 + (i % 7),
                "price": 120.0,
                "cost": 50.0,
            }
        )
    df = pd.DataFrame(data)
    csv_path = Path(__file__).parent / "temp_test_data.csv"
    df.to_csv(csv_path, index=False)

    db = SessionLocal()

    # Clean up existing test data if any
    existing_prod = db.query(Product).filter(Product.sku == "SKU-TEST-999").first()
    if existing_prod:
        db.query(Alert).filter(Alert.product_id == existing_prod.id).delete()
        db.query(RiskScore).filter(RiskScore.product_id == existing_prod.id).delete()
        db.query(Forecast).filter(Forecast.product_id == existing_prod.id).delete()
        db.query(Sale).filter(Sale.product_id == existing_prod.id).delete()
        db.query(InventoryItem).filter(
            InventoryItem.product_id == existing_prod.id
        ).delete()
        db.query(Product).filter(Product.sku == "SKU-TEST-999").delete()
        db.commit()

    try:
        # 2. Run the pipeline
        res = run_training_pipeline(db, csv_path, username="test_runner")
        assert res["success"] is True
        assert "SKU-TEST-999" in res["processed_skus"]

        # 3. Verify DB updates
        prod = db.query(Product).filter(Product.sku == "SKU-TEST-999").first()
        assert prod is not None
        assert prod.base_price == 120.0
        assert prod.unit_cost == 50.0

        # Check sales history
        sales_count = db.query(Sale).filter(Sale.product_id == prod.id).count()
        assert sales_count == 60

        # Check forecast entries
        forecast_count = (
            db.query(Forecast).filter(Forecast.product_id == prod.id).count()
        )
        assert forecast_count == 30

        # Check risk score calculations
        risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
        assert risk is not None
        assert risk.revenue_at_risk >= 0
        assert risk.profit_at_risk >= 0

    finally:
        # 4. Cleanup test data
        prod = db.query(Product).filter(Product.sku == "SKU-TEST-999").first()
        if prod:
            db.query(Alert).filter(Alert.product_id == prod.id).delete()
            db.query(RiskScore).filter(RiskScore.product_id == prod.id).delete()
            db.query(Forecast).filter(Forecast.product_id == prod.id).delete()
            db.query(Sale).filter(Sale.product_id == prod.id).delete()
            db.query(InventoryItem).filter(InventoryItem.product_id == prod.id).delete()
            db.query(Product).filter(Product.sku == "SKU-TEST-999").delete()
            db.commit()
        db.close()

        if csv_path.exists():
            csv_path.unlink()


def test_api_dataset_upload_triggers_pipeline():
    # 1. Register and Login to get auth token
    register_payload = {
        "email": "pipeline_tester@retailgpt.com",
        "username": "pipe_tester",
        "full_name": "Pipeline Tester",
        "password": "testpassword123",
        "role": "admin",
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "pipe_tester", "password": "testpassword123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Prepare mock CSV data
    data = []
    start_date = datetime.utcnow() - timedelta(days=60)
    for i in range(60):
        t_date = start_date + timedelta(days=i)
        data.append(
            {
                "product_id": "SKU-UPLOAD-777",
                "date": t_date.strftime("%Y-%m-%d"),
                "quantity": 15 + (i % 5),
                "price": 200.0,
                "cost": 90.0,
            }
        )
    df = pd.DataFrame(data)
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    # Ensure clean database state
    db = SessionLocal()
    existing_prod = db.query(Product).filter(Product.sku == "SKU-UPLOAD-777").first()
    if existing_prod:
        db.query(Alert).filter(Alert.product_id == existing_prod.id).delete()
        db.query(RiskScore).filter(RiskScore.product_id == existing_prod.id).delete()
        db.query(Forecast).filter(Forecast.product_id == existing_prod.id).delete()
        db.query(Sale).filter(Sale.product_id == existing_prod.id).delete()
        db.query(InventoryItem).filter(
            InventoryItem.product_id == existing_prod.id
        ).delete()
        db.query(Product).filter(Product.sku == "SKU-UPLOAD-777").delete()
        db.commit()

    try:
        # 3. Post file to /upload API endpoint
        files = {"file": ("test_upload.csv", csv_bytes, "text/csv")}
        response = client.post("/api/dataset/upload", files=files, headers=headers)
        assert response.status_code == 200
        upload_json = response.json()
        assert upload_json["success"] is True
        temp_file_id = upload_json["temp_file_id"]

        # 4. Trigger /import with mapped headers
        import_payload = {
            "temp_file_id": temp_file_id,
            "source_type": "csv",
            "mapping": {
                "sku": "product_id",
                "date": "date",
                "current_stock": "quantity",
                "unit_price": "price",
                "unit_cost": "cost",
            },
        }
        import_response = client.post(
            "/api/dataset/import", json=import_payload, headers=headers
        )
        assert import_response.status_code == 200
        assert import_response.json()["success"] is True

        # TestClient runs background tasks synchronously. So the product should be in database now!
        prod = db.query(Product).filter(Product.sku == "SKU-UPLOAD-777").first()
        assert prod is not None
        assert prod.base_price == 200.0

        # Verify forecast entries
        forecast_count = (
            db.query(Forecast).filter(Forecast.product_id == prod.id).count()
        )
        assert forecast_count == 30

        # Verify risk score
        risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
        assert risk is not None
        assert risk.revenue_at_risk >= 0

    finally:
        # Clean up
        prod = db.query(Product).filter(Product.sku == "SKU-UPLOAD-777").first()
        if prod:
            db.query(Alert).filter(Alert.product_id == prod.id).delete()
            db.query(RiskScore).filter(RiskScore.product_id == prod.id).delete()
            db.query(Forecast).filter(Forecast.product_id == prod.id).delete()
            db.query(Sale).filter(Sale.product_id == prod.id).delete()
            db.query(InventoryItem).filter(InventoryItem.product_id == prod.id).delete()
            db.query(Product).filter(Product.sku == "SKU-UPLOAD-777").delete()
            db.commit()

        # Cleanup user
        user = db.query(User).filter(User.username == "pipe_tester").first()
        if user:
            db.delete(user)
            db.commit()

        db.close()

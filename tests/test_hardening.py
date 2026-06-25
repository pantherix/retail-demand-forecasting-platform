import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app import app
from backend.copilot.service import copilot
from backend.database.models import (
    Alert,
    Dataset,
    Forecast,
    InventoryItem,
    Product,
    RiskScore,
    Sale,
    User,
)
from backend.database.session import SessionLocal

client = TestClient(app)


def test_lineage_cleanup_safety():
    db = SessionLocal()

    # 1. Register a test dataset
    batch_id = str(uuid.uuid4())
    dataset_name = "Hardening Test Sync"
    filename = "hardening_test.csv"

    ds = Dataset(
        name=dataset_name,
        filename=filename,
        rows=10,
        columns=5,
        sku_count=3,
        quality_score=95.0,
        date_from="2026-06-01",
        date_to="2026-06-10",
        owner="admin",
        import_batch_id=batch_id,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    ds_id = ds.id

    # 2. Add product with valid lineage
    prod_valid = Product(
        sku="MAT-2001",
        name="Valid Material SKU",
        category="Hardening",
        base_price=150.0,
        unit_cost=70.0,
        lead_time_days=5,
        created_by_import=True,
        import_batch_id=batch_id,
        import_timestamp=datetime.utcnow(),
    )

    # 3. Add product with failed lineage (import_batch_id is not in Datasets)
    prod_failed_lineage = Product(
        sku="SKU-FAILED-INGESTION",
        name="Failed Ingestion SKU",
        category="Hardening",
        base_price=100.0,
        unit_cost=40.0,
        lead_time_days=5,
        created_by_import=True,
        import_batch_id="failed-batch-uuid",
        import_timestamp=datetime.utcnow(),
    )

    # 4. Add product with metadata corruption (negative unit cost)
    prod_corrupted = Product(
        sku="SKU-CORRUPTED",
        name="Corrupted SKU",
        category="Hardening",
        base_price=100.0,
        unit_cost=-50.0,  # Negative cost
        lead_time_days=5,
        created_by_import=True,
        import_batch_id=batch_id,
        import_timestamp=datetime.utcnow(),
    )

    # 5. Add manual/seeded product (survives by default since created_by_import is False)
    prod_manual1 = Product(
        sku="10001",
        name="Manual Item 1",
        category="Manual",
        base_price=200.0,
        unit_cost=100.0,
        lead_time_days=5,
        created_by_import=False,
    )
    prod_manual2 = Product(
        sku="ITEM0001",
        name="Manual Item 2",
        category="Manual",
        base_price=200.0,
        unit_cost=100.0,
        lead_time_days=5,
        created_by_import=False,
    )

    db.add_all(
        [prod_valid, prod_failed_lineage, prod_corrupted, prod_manual1, prod_manual2]
    )
    db.commit()

    # Refresh to get IDs
    db.refresh(prod_valid)
    db.refresh(prod_failed_lineage)
    db.refresh(prod_corrupted)
    db.refresh(prod_manual1)
    db.refresh(prod_manual2)

    # Add alerts/forecasts to test cascade/lineage deletion on failed lineage product
    alert_failed = Alert(
        product_id=prod_failed_lineage.id,
        type="Stockout Risk",
        message="Alert on failed lineage SKU",
        created_by_import=True,
        import_batch_id="failed-batch-uuid",
    )
    db.add(alert_failed)
    db.commit()
    alert_failed_id = alert_failed.id

    try:
        # Create user for auth context
        register_payload = {
            "email": "hardening_tester@retailgpt.com",
            "username": "hard_tester",
            "full_name": "Hardening Tester",
            "password": "testpassword123",
            "role": "admin",
        }
        client.post("/api/auth/register", json=register_payload)
        login_resp = client.post(
            "/api/auth/login",
            data={"username": "hard_tester", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Phase 1: Audit mode (confirm = False)
        audit_resp = client.post("/api/dataset/cleanup?confirm=false", headers=headers)
        assert audit_resp.status_code == 200
        audit_data = audit_resp.json()
        assert audit_data["confirmed"] is False
        assert (
            "SKU-FAILED-INGESTION" in audit_data["audit_report"]["products_to_remove"]
        )
        assert "SKU-CORRUPTED" in audit_data["audit_report"]["products_to_remove"]
        assert "MAT-2001" not in audit_data["audit_report"]["products_to_remove"]
        assert "10001" not in audit_data["audit_report"]["products_to_remove"]

        # Verify survivor proof in output
        assert audit_data["proof_survivors"]["10001"] is True
        assert audit_data["proof_survivors"]["MAT-2001"] is True
        assert audit_data["proof_survivors"]["ITEM0001"] is True

        # Phase 2: Execution mode (confirm = True)
        cleanup_resp = client.post("/api/dataset/cleanup?confirm=true", headers=headers)
        assert cleanup_resp.status_code == 200
        cleanup_data = cleanup_resp.json()
        assert cleanup_data["confirmed"] is True

        # Verify deletions
        db.expire_all()
        # SKU-FAILED-INGESTION must be deleted
        deleted_prod1 = (
            db.query(Product).filter(Product.sku == "SKU-FAILED-INGESTION").first()
        )
        assert deleted_prod1 is None
        # SKU-CORRUPTED must be deleted
        deleted_prod2 = db.query(Product).filter(Product.sku == "SKU-CORRUPTED").first()
        assert deleted_prod2 is None
        # MAT-2001, 10001, ITEM0001 must survive
        assert db.query(Product).filter(Product.sku == "MAT-2001").first() is not None
        assert db.query(Product).filter(Product.sku == "10001").first() is not None
        assert db.query(Product).filter(Product.sku == "ITEM0001").first() is not None

        # Alert associated with failed lineage should be gone
        assert db.query(Alert).filter(Alert.id == alert_failed_id).first() is None

    finally:
        # Cleanup any remaining
        for sku in [
            "MAT-2001",
            "SKU-FAILED-INGESTION",
            "SKU-CORRUPTED",
            "10001",
            "ITEM0001",
        ]:
            p = db.query(Product).filter(Product.sku == sku).first()
            if p:
                db.query(Alert).filter(Alert.product_id == p.id).delete()
                db.query(RiskScore).filter(RiskScore.product_id == p.id).delete()
                db.query(Forecast).filter(Forecast.product_id == p.id).delete()
                db.query(Sale).filter(Sale.product_id == p.id).delete()
                db.query(InventoryItem).filter(
                    InventoryItem.product_id == p.id
                ).delete()
                db.query(Product).filter(Product.id == p.id).delete()
        db.query(Dataset).filter(Dataset.id == ds_id).delete()

        user = db.query(User).filter(User.username == "hard_tester").first()
        if user:
            db.delete(user)
        db.commit()
        db.close()


def test_provider_failover_flow():
    db = SessionLocal()
    try:
        # Temporarily mock LLM_PROVIDER as groq and set an invalid groq key
        os.environ["LLM_PROVIDER"] = "groq"
        os.environ["GROQ_API_KEY"] = "invalid_key_to_force_failure"

        # Execute chat. Even with invalid Groq key, it should failover to Rule-based engine
        res = copilot.chat("What should I order today?", db)
        assert res is not None
        assert "answer" in res
        assert "insight" in res
        assert "recommendation" in res
        assert "financial_impact" in res

        # Check that it executed rule-based response properly
        assert "suggested to approve purchase orders" in res["recommendation"].lower()
    finally:
        db.close()
        # Reset provider setting
        os.environ["LLM_PROVIDER"] = "openai"
        if "GROQ_API_KEY" in os.environ:
            del os.environ["GROQ_API_KEY"]


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["status"] in ["green", "yellow", "red"]
    assert "details" in data
    assert "database" in data["details"]


def test_strict_mapping_validation_and_scoring():
    import io

    csv_data = (
        "Customer ID,Date,Current Stock,Revenue\n"
        "CUST-001,2026-06-01,100,500\n"
        "CUST-002,2026-06-02,200,1000\n"
    )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "hard_tester").first()
        if not user:
            register_payload = {
                "email": "hardening_tester@retailgpt.com",
                "username": "hard_tester",
                "full_name": "Hardening Tester",
                "password": "testpassword123",
                "role": "admin",
            }
            client.post("/api/auth/register", json=register_payload)

        login_resp = client.post(
            "/api/auth/login",
            data={"username": "hard_tester", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Upload the file
        upload_resp = client.post(
            "/api/dataset/upload",
            files={
                "file": (
                    "test_mapping.csv",
                    io.BytesIO(csv_data.encode("utf-8")),
                    "text/csv",
                )
            },
            headers=headers,
        )
        assert upload_resp.status_code == 200
        upload_info = upload_resp.json()
        temp_file_id = upload_info["temp_file_id"]

        # Test case A: Block customer identifiers mapped to sku
        import_payload = {
            "temp_file_id": temp_file_id,
            "source_type": "csv",
            "mapping": {
                "sku": "Customer ID",
                "date": "Date",
                "current_stock": "Current Stock",
                "revenue": "Revenue",
            },
            "confirm_low_confidence": True,
        }
        resp = client.post("/api/dataset/import", json=import_payload, headers=headers)
        assert resp.status_code == 400
        assert "customer identifiers" in resp.json()["detail"].lower()

        # Test case B: Block invalid source column name for sku
        csv_data_invalid_sku = (
            "Code XYZ,Date,Current Stock,Revenue\n" "SKU-001,2026-06-01,100,500\n"
        )
        upload_resp = client.post(
            "/api/dataset/upload",
            files={
                "file": (
                    "test_invalid_sku.csv",
                    io.BytesIO(csv_data_invalid_sku.encode("utf-8")),
                    "text/csv",
                )
            },
            headers=headers,
        )
        temp_file_id = upload_resp.json()["temp_file_id"]

        import_payload = {
            "temp_file_id": temp_file_id,
            "source_type": "csv",
            "mapping": {
                "sku": "Code XYZ",
                "date": "Date",
                "current_stock": "Current Stock",
                "revenue": "Revenue",
            },
            "confirm_low_confidence": True,
        }
        resp = client.post("/api/dataset/import", json=import_payload, headers=headers)
        assert resp.status_code == 400
        assert "invalid source column name for 'sku'" in resp.json()["detail"].lower()

        # Test case C: Check confidence score validation rejection
        csv_data_confidence = "SKU,Date,Stock,Revenue\n" "SKU-100,2026-06-01,100,500\n"
        upload_resp = client.post(
            "/api/dataset/upload",
            files={
                "file": (
                    "test_confidence.csv",
                    io.BytesIO(csv_data_confidence.encode("utf-8")),
                    "text/csv",
                )
            },
            headers=headers,
        )
        temp_file_id = upload_resp.json()["temp_file_id"]

        import_payload = {
            "temp_file_id": temp_file_id,
            "source_type": "csv",
            "mapping": {
                "sku": "SKU",
                "date": "Date",
                "current_stock": "Revenue",  # Revenue is extremely low confidence for current_stock
            },
            "confirm_low_confidence": False,
        }
        resp = client.post("/api/dataset/import", json=import_payload, headers=headers)
        assert resp.status_code == 400
        assert "low confidence mapping" in resp.json()["detail"].lower()

        # Test case D: Check realistic quality score penalty calculation
        csv_data_warnings = (
            "SKU,Date,Stock,Revenue\n"
            "SKU-100,2026-06-01,-10,500\n"
            "SKU-100,2026-06-01,100,-500\n"
        )
        upload_resp = client.post(
            "/api/dataset/upload",
            files={
                "file": (
                    "test_warnings.csv",
                    io.BytesIO(csv_data_warnings.encode("utf-8")),
                    "text/csv",
                )
            },
            headers=headers,
        )
        temp_file_id = upload_resp.json()["temp_file_id"]

        import_payload = {
            "temp_file_id": temp_file_id,
            "source_type": "csv",
            "mapping": {
                "sku": "SKU",
                "date": "Date",
                "current_stock": "Stock",
                "revenue": "Revenue",
            },
            "confirm_low_confidence": True,
        }
        resp = client.post("/api/dataset/import", json=import_payload, headers=headers)
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["success"] is True
        assert res_data["quality_score"] == 92.0

    finally:
        db.query(Dataset).filter(Dataset.owner == "hard_tester").delete()
        db.commit()
        db.close()

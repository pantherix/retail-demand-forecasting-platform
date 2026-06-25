from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app import app
from backend.copilot.rag import generate_db_facts, retrieve_relevant_facts
from backend.copilot.service import copilot
from backend.database.session import SessionLocal

client = TestClient(app)


def test_generate_db_facts():
    db = SessionLocal()
    try:
        facts = generate_db_facts(db)
        assert len(facts) > 0

        # Verify that the generated facts contain seed details
        assert any("SKU-101" in f for f in facts)
        assert any("Warehouse A" in f for f in facts)
        assert any("reliability score" in f for f in facts)

    finally:
        db.close()


def test_retrieve_relevant_facts():
    db = SessionLocal()
    try:
        # 1. Search for warehouse capacity
        facts = retrieve_relevant_facts(db, "warehouse capacity utilization", top_k=2)
        assert len(facts) > 0
        assert any("Warehouse" in f for f in facts)

        # 2. Search for SKU-101
        facts = retrieve_relevant_facts(db, "SKU-101 stock safety", top_k=2)
        assert len(facts) > 0
        assert any("SKU-101" in f for f in facts)

    finally:
        db.close()


def test_copilot_rag_chat():
    db = SessionLocal()
    try:
        # 1. Test Order Reorder Query
        res = copilot.chat("What should I order today?", db)
        assert "insight" in res
        assert "recommendation" in res
        assert "financial_impact" in res

        # 2. Test Warehouse Utilization Query
        res = copilot.chat("Is any warehouse capacity full?", db)
        assert "insight" in res

        # 3. Test SKU-specific query
        res = copilot.chat("Show status for SKU-205", db)
        assert "insight" in res
        assert "SKUs requiring replenishment" in res["insight"]

    finally:
        db.close()


def test_copilot_chat_api_endpoint():
    # Login user
    register_payload = {
        "email": "rag_tester@retailgpt.com",
        "username": "rag_tester",
        "full_name": "RAG Tester",
        "password": "testpassword123",
        "role": "admin",
    }
    client.post("/api/auth/register", json=register_payload)
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "rag_tester", "password": "testpassword123"},
    )
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = client.post(
            "/api/enterprise/copilot/chat",
            json={"prompt": "What should I order?"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "insight" in data
        assert "recommendation" in data
        assert "financial_impact" in data

    finally:
        db = SessionLocal()
        from backend.database.models import User

        user = db.query(User).filter(User.username == "rag_tester").first()
        if user:
            db.delete(user)
            db.commit()
        db.close()

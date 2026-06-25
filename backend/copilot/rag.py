from __future__ import annotations

import logging
import os
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sqlalchemy.orm import Session

from backend.database.models import (
    Alert,
    InventoryItem,
    Product,
    PurchaseOrder,
    RiskScore,
    Supplier,
    Warehouse,
)

logger = logging.getLogger(__name__)


def generate_db_facts(db: Session) -> List[str]:
    """
    Compiles database tables into factual textual strings.
    """
    facts = []

    # 1. Product Stock and Exposure Metrics
    products = db.query(Product).all()
    for prod in products:
        # Sum stock
        inv_items = (
            db.query(InventoryItem).filter(InventoryItem.product_id == prod.id).all()
        )
        stock = sum(item.current_stock for item in inv_items)

        # Risk values
        risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
        rev_risk = risk.revenue_at_risk if risk else 0.0
        prof_risk = risk.profit_at_risk if risk else 0.0
        action = risk.recommended_action if risk else "Monitor"
        days_cover = (
            stock / (prod.reorder_point / max(prod.lead_time_days, 1))
            if prod.reorder_point > 0
            else 99.0
        )

        fact_str = (
            f"Product SKU {prod.sku} ({prod.name}) is in category '{prod.category}'. "
            f"Current inventory level is {stock:.0f} units. Safety stock: {prod.safety_stock:.0f} units, reorder point: {prod.reorder_point:.0f} units. "
            f"Days of cover: {days_cover:.1f} days. Recommended decision action: '{action}'. "
            f"Financial exposure is ₹{rev_risk:,.2f} revenue at risk and ₹{prof_risk:,.2f} profit at risk. "
            f"Capital value of this stock is ₹{(stock * prod.unit_cost):,.2f} (ABC Class {prod.abc_class})."
        )
        facts.append(fact_str)

    # 2. Supplier Performance
    suppliers = db.query(Supplier).all()
    for sup in suppliers:
        fact_str = (
            f"Supplier '{sup.name}' provides products with an average lead time of {sup.lead_time_days} days. "
            f"Supplier reliability score: {sup.reliability_score:.1f}% and fill rate: {sup.fill_rate:.1f}%."
        )
        facts.append(fact_str)

    # 3. Active Alerts
    alerts = db.query(Alert).filter(Alert.status == "Active").all()
    for al in alerts:
        fact_str = (
            f"Active Alert: SKU {al.product.sku} has alert type '{al.type}' with message: '{al.message}'. "
            f"Severity: {al.severity}."
        )
        facts.append(fact_str)

    # 4. Warehouse Status
    warehouses = db.query(Warehouse).all()
    for wh in warehouses:
        fact_str = (
            f"Warehouse '{wh.name}' is located in '{wh.location}'. "
            f"Capacity is {wh.capacity:.0f} units, and current capacity utilization is {wh.utilization:.1f}%."
        )
        facts.append(fact_str)

    # 5. Pending Purchase Orders
    pos = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.status.in_(["Draft", "Pending Approval", "Ordered"]))
        .all()
    )
    for po in pos:
        items_desc = ", ".join(
            [f"{item['sku']}: {item['quantity']:.0f} units" for item in po.details]
        )
        fact_str = (
            f"Purchase Order PO-{po.id} for supplier '{po.supplier.name}' is in status '{po.status}' "
            f"with total cost ₹{po.total_cost:,.2f}. Items ordered: {items_desc}."
        )
        facts.append(fact_str)

    # Append general platform details
    facts.append("The platform currency is Indian Rupee (₹).")
    facts.append(
        "Users currently logged in: admin (role: admin), manager (role: manager), analyst (role: analyst)."
    )

    return facts


def retrieve_relevant_facts(db: Session, query: str, top_k: int = 5) -> List[str]:
    """
    Retrieves the top K database facts relevant to the query.
    First tries OpenAI embeddings if key is configured, falls back to local TF-IDF vector space.
    """
    facts = generate_db_facts(db)
    if not facts:
        return []

    openai_key = os.getenv("OPENAI_API_KEY", "")
    use_openai = openai_key and openai_key != "your-openai-key-here"

    if use_openai:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)

            # Combine query and facts for batch embedding
            texts = [query] + facts
            res = client.embeddings.create(input=texts, model="text-embedding-3-small")

            embeddings = [record.embedding for record in res.data]
            query_emb = np.array(embeddings[0])
            fact_embs = np.array(embeddings[1:])

            # Compute Cosine Similarity
            dots = np.dot(fact_embs, query_emb)
            norms = np.linalg.norm(fact_embs, axis=1) * np.linalg.norm(query_emb)
            scores = dots / np.where(norms == 0, 1e-9, norms)

            # Get top indices
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [facts[idx] for idx in top_indices]
        except Exception as e:
            logger.warning(
                "OpenAI Embeddings retrieval failed, falling back to local TF-IDF: %s",
                e,
            )

    # Local TF-IDF Vector Space Fallback
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(facts)
        query_vec = vectorizer.transform([query])

        # Calculate cosine similarity
        scores = (tfidf_matrix * query_vec.T).toarray().flatten()
        top_indices = np.argsort(scores)[::-1]

        retrieved = []
        for idx in top_indices:
            if len(retrieved) >= top_k:
                break
            # Only include if there is some overlap (score > 0)
            if scores[idx] > 0.0:
                retrieved.append(facts[idx])

        # If no word matches, return the top_k alerts or risk scores as context
        if not retrieved:
            retrieved = facts[:top_k]

        return retrieved
    except Exception as e:
        logger.error("TF-IDF vector matching failed: %s", e)
        return facts[:top_k]

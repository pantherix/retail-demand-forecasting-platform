from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.risk.ranking import risk_engine

router = APIRouter(prefix="/risk", tags=["Risk"])


class Product(BaseModel):

    sku: str

    forecast: float

    stock: float

    revenue: float


class RiskRequest(BaseModel):

    products: List[Product]


@router.get("/health")
def health():

    return {"module": "risk", "status": "healthy"}


@router.post("/rank")
def rank_products(payload: RiskRequest):

    try:

        products = [item.model_dump() for item in payload.products]

        rankings = risk_engine.rank(products)

        return {"success": True, "rankings": rankings}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/critical")
def critical_products(payload: RiskRequest):

    try:

        products = [item.model_dump() for item in payload.products]

        critical = risk_engine.critical_only(products)

        return {"count": len(critical), "critical": critical}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/top10")
def top_10_products(payload: RiskRequest):

    try:

        products = [item.model_dump() for item in payload.products]

        rankings = risk_engine.rank(products)

        return {"top10": rankings[:10]}

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard")
def dashboard(payload: RiskRequest):

    try:

        products = [item.model_dump() for item in payload.products]

        rankings = risk_engine.rank(products)

        critical = len([x for x in rankings if x["risk"] == "CRITICAL"])

        high = len([x for x in rankings if x["risk"] == "HIGH"])

        medium = len([x for x in rankings if x["risk"] == "MEDIUM"])

        low = len([x for x in rankings if x["risk"] == "LOW"])

        return {
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "top_risks": rankings[:5],
        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))

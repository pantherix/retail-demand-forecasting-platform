from fastapi import APIRouter
from pydantic import BaseModel

from copilot.service import copilot

router = APIRouter(prefix="/copilot", tags=["Copilot"])


class CopilotExplainRequest(BaseModel):
    sku: str
    forecast: float
    stock: float


class CopilotAnalyzeRequest(BaseModel):
    sku: str
    forecast: float
    stock: float
    price: float = 100.0


@router.get("/health")
def health():
    return {"module": "copilot", "status": "healthy"}


@router.post("/explain")
def explain(payload: CopilotExplainRequest):
    answer = copilot.explain(payload.sku, payload.forecast, payload.stock)
    return {"sku": payload.sku, "explanation": answer}


@router.post("/analyze")
def analyze(payload: CopilotAnalyzeRequest):
    result = copilot.analyze_forecast(
        sku=payload.sku,
        forecast=payload.forecast,
        stock=payload.stock,
        price=payload.price,
    )
    return result

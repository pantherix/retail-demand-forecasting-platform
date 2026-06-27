from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from forecasting.trainer import ForecastTrainer
from forecasting.predictor import ForecastPredictor, ModelRegistry
from copilot.service import copilot

router = APIRouter(prefix="/forecast", tags=["Forecasting"])

trainer = ForecastTrainer()
predictor = ForecastPredictor()
registry = ModelRegistry()


class TrainRequest(BaseModel):
    sku: str
    csv_path: str


class ForecastRequest(BaseModel):
    sku: str
    history_path: str
    horizon: int = Field(default=30, ge=1, le=365)


class BatchForecastRequest(BaseModel):
    skus: List[str]
    horizon: int = Field(default=30, ge=1, le=365)


@router.get("/health")
def health():
    return {"module": "forecasting", "status": "healthy"}


def validate_safe_path(user_path: str) -> Path:
    try:
        resolved_path = Path(user_path).resolve(strict=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid file path. File does not exist.")
    approved_root = Path(__file__).resolve().parents[2]
    try:
        resolved_path.relative_to(approved_root)
        return resolved_path
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path. File must be inside the workspace directory.")


@router.post("/train")
def train_model(payload: TrainRequest):
    try:
        csv_path = validate_safe_path(payload.csv_path)
        df = pd.read_csv(csv_path)
        metrics = trainer.train_xgboost(df, payload.sku)
        registry.register(payload.sku, "xgboost", metrics)
        return {"success": True, "metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict")
def predict(payload: ForecastRequest):
    try:
        history_path = validate_safe_path(payload.history_path)
        history = pd.read_csv(history_path)
        result = predictor.forecast_horizon(payload.sku, history, payload.horizon)
        forecasts = [row["forecast"] for row in result["forecasts"]]
        confidence = predictor.confidence_interval(forecasts)
        return {
            "success": True,
            "forecast": result,
            "confidence": confidence,
            "mean": confidence["mean"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
def batch_forecast(payload: BatchForecastRequest):
    output = []
    for sku in payload.skus:
        file = f"data/tslib/{sku}.csv"
        try:
            history = pd.read_csv(file)
            forecast = predictor.forecast_horizon(sku, history, payload.horizon)
            output.append(forecast)
        except Exception:
            continue
    return {"count": len(output), "results": output}


@router.get("/leaderboard")
def leaderboard():
    results = []
    registry_path = Path("artifacts/registry")
    if not registry_path.exists():
        return []
    for file in registry_path.glob("*.json"):
        with open(file, "r") as fp:
            results.append(json.load(fp))
    return sorted(results, key=lambda x: x.get("metrics", {}).get("rmse", 999999))


@router.get("/sku/{sku}")
def sku_analytics(sku: str):
    model = registry.load(sku)
    if not model:
        raise HTTPException(status_code=404, detail=f"No trained model found for SKU: {sku}")
    return model


@router.post("/executive-summary")
def executive_summary(payload: ForecastRequest):
    try:
        history_path = validate_safe_path(payload.history_path)
        history = pd.read_csv(history_path)
        result = predictor.forecast_horizon(payload.sku, history, payload.horizon)
        forecasts = [x["forecast"] for x in result["forecasts"]]
        avg_forecast = sum(forecasts) / len(forecasts) if forecasts else 0
        analysis = copilot.analyze_forecast(
            sku=payload.sku, forecast=avg_forecast, stock=avg_forecast * 0.7, price=100
        )
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

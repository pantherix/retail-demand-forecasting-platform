from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from database.repositories import TrainingRepository, ForecastRepository
from auth.dependencies import get_current_user
from database.models import User

router = APIRouter(prefix="/leaderboard", tags=["Model Leaderboard"])


@router.get("/health")
def health():
    return {"module": "leaderboard", "status": "healthy"}


@router.get("/models")
def model_leaderboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns all training runs sorted by RMSE — the model leaderboard."""
    runs = TrainingRepository(db).leaderboard()
    return [
        {
            "rank":       i + 1,
            "sku":        r.sku,
            "model":      r.model_name,
            "rmse":       r.rmse,
            "mae":        r.mae,
            "mape":       r.mape,
            "samples":    r.samples,
            "trained_at": str(r.trained_at),
        }
        for i, r in enumerate(runs)
    ]


@router.get("/sku/{sku}")
def sku_history(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All training runs for a specific SKU, newest first."""
    runs = TrainingRepository(db).get_by_sku(sku)
    if not runs:
        raise HTTPException(status_code=404, detail=f"No training runs found for SKU: {sku}")
    return [
        {
            "sku":        r.sku,
            "model":      r.model_name,
            "rmse":       r.rmse,
            "mae":        r.mae,
            "mape":       r.mape,
            "trained_at": str(r.trained_at),
        }
        for r in runs
    ]


@router.get("/forecasts/{sku}")
def forecast_history(
    sku: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Forecast run history for a SKU."""
    runs = ForecastRepository(db).get_by_sku(sku)
    if not runs:
        raise HTTPException(status_code=404, detail=f"No forecasts found for SKU: {sku}")
    return [
        {
            "sku":            r.sku,
            "model":          r.model_name,
            "horizon":        r.horizon,
            "total_forecast": r.total_forecast,
            "mape":           r.mape,
            "created_at":     str(r.created_at),
        }
        for r in runs
    ]


@router.get("/simulations")
def simulation_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from database.repositories import SimulationRepository
    runs = SimulationRepository(db).get_recent(50)
    return [
        {
            "sku":              r.sku,
            "scenario":         r.scenario_name,
            "baseline":         r.baseline_forecast,
            "simulated_demand": r.simulated_demand,
            "revenue":          r.revenue,
            "stockout_risk":    r.stockout_risk,
            "created_at":       str(r.created_at),
        }
        for r in runs
    ]

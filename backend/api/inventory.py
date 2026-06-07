from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from inventory.optimizer import InventoryOptimizer
from inventory.reorder import ReorderPlanner

router = APIRouter(prefix="/inventory", tags=["Inventory"])

optimizer = InventoryOptimizer()
planner = ReorderPlanner()


class InventoryRequest(BaseModel):
    forecast: float = Field(..., gt=0, description="30-day demand forecast")
    stock: float = Field(..., ge=0, description="Current stock on hand")


class OptimizeRequest(BaseModel):
    forecast: float = Field(..., gt=0)
    current_stock: float = Field(..., ge=0)
    demand_std: float = Field(default=20.0, ge=0)
    lead_time_days: int = Field(default=7, ge=1)
    ordering_cost: float = Field(default=100.0, ge=0)
    holding_cost: float = Field(default=5.0, ge=0)


@router.get("/health")
def health():
    return {"module": "inventory", "status": "healthy"}


@router.post("/reorder")
def reorder(payload: InventoryRequest):
    return planner.calculate(payload.forecast, payload.stock)


@router.post("/optimize")
def optimize(payload: OptimizeRequest):
    try:
        result = optimizer.optimize(
            forecast=payload.forecast,
            current_stock=payload.current_stock,
            demand_std=payload.demand_std,
            lead_time_days=payload.lead_time_days,
            ordering_cost=payload.ordering_cost,
            holding_cost=payload.holding_cost,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-score")
def health_score(payload: InventoryRequest):
    score = optimizer.inventory_health_score(payload.stock, payload.forecast)
    stockout_risk = optimizer.stockout_probability(payload.stock, payload.forecast)
    return {
        "forecast": payload.forecast,
        "stock": payload.stock,
        "health_score": score,
        "stockout_risk_pct": stockout_risk,
    }

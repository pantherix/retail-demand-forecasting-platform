from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from database.models import (
    User, Dataset, ForecastRun, TrainingRun,
    SimulationRun, Report, AuditLog,
)


# ── User Repository ───────────────────────────────────────────────────────────
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, email: str, username: str, full_name: str, hashed_pw: str, role: str = "analyst") -> User:
        user = User(email=email, username=username, full_name=full_name, hashed_pw=hashed_pw, role=role)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_all(self) -> List[User]:
        return self.db.query(User).all()


# ── Dataset Repository ────────────────────────────────────────────────────────
class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, filename: str, rows: int, columns: int,
               sku_count: int, quality_score: float, date_from: str,
               date_to: str, owner: str) -> Dataset:
        ds = Dataset(
            name=name, filename=filename, rows=rows, columns=columns,
            sku_count=sku_count, quality_score=quality_score,
            date_from=date_from, date_to=date_to, owner=owner,
        )
        self.db.add(ds)
        self.db.commit()
        self.db.refresh(ds)
        return ds

    def get_all(self) -> List[Dataset]:
        return self.db.query(Dataset).order_by(Dataset.uploaded_at.desc()).all()

    def get_by_id(self, id: int) -> Optional[Dataset]:
        return self.db.query(Dataset).filter(Dataset.id == id).first()


# ── Forecast Repository ───────────────────────────────────────────────────────
class ForecastRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, sku: str, model_name: str, horizon: int, total_forecast: float,
             mae: float, rmse: float, mape: float, dataset_id: int = None) -> ForecastRun:
        run = ForecastRun(
            sku=sku, model_name=model_name, horizon=horizon,
            total_forecast=total_forecast, mae=mae, rmse=rmse, mape=mape,
            dataset_id=dataset_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_sku(self, sku: str) -> List[ForecastRun]:
        return self.db.query(ForecastRun).filter(ForecastRun.sku == sku)\
            .order_by(ForecastRun.created_at.desc()).all()

    def get_latest(self, sku: str) -> Optional[ForecastRun]:
        return self.db.query(ForecastRun).filter(ForecastRun.sku == sku)\
            .order_by(ForecastRun.created_at.desc()).first()


# ── Training Run Repository ───────────────────────────────────────────────────
class TrainingRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, sku: str, model_name: str, rmse: float, mae: float,
             mape: float, samples: int, features: int,
             model_path: str, dataset_id: int = None) -> TrainingRun:
        run = TrainingRun(
            sku=sku, model_name=model_name, rmse=rmse, mae=mae,
            mape=mape, samples=samples, features=features,
            model_path=model_path, dataset_id=dataset_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def leaderboard(self) -> List[TrainingRun]:
        return self.db.query(TrainingRun).order_by(TrainingRun.rmse).all()

    def get_by_sku(self, sku: str) -> List[TrainingRun]:
        return self.db.query(TrainingRun).filter(TrainingRun.sku == sku)\
            .order_by(TrainingRun.trained_at.desc()).all()


# ── Simulation Repository ─────────────────────────────────────────────────────
class SimulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, sku: str, scenario_name: str, baseline_forecast: float,
             simulated_demand: float, revenue: float, profit: float,
             stockout_risk: str, inventory_gap: float, params: dict) -> SimulationRun:
        run = SimulationRun(
            sku=sku, scenario_name=scenario_name,
            baseline_forecast=baseline_forecast,
            simulated_demand=simulated_demand,
            revenue=revenue, profit=profit,
            stockout_risk=stockout_risk, inventory_gap=inventory_gap,
            params=params,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_recent(self, limit: int = 20) -> List[SimulationRun]:
        return self.db.query(SimulationRun)\
            .order_by(SimulationRun.created_at.desc()).limit(limit).all()


# ── Audit Repository ──────────────────────────────────────────────────────────
class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, user: str, action: str, resource: str,
            detail: str = "", ip_address: str = "") -> AuditLog:
        entry = AuditLog(
            user=user, action=action, resource=resource,
            detail=detail, ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_recent(self, limit: int = 50) -> List[AuditLog]:
        return self.db.query(AuditLog)\
            .order_by(AuditLog.created_at.desc()).limit(limit).all()

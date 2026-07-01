from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from backend.database.models import (
    AuditLog,
    Dataset,
    ForecastRun,
    SimulationRun,
    TrainingRun,
    User,
)


# ── User Repository ───────────────────────────────────────────────────────────
class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        email: str,
        username: str,
        full_name: str,
        hashed_pw: str,
        role: str = "analyst",
    ) -> User:
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_pw=hashed_pw,
            role=role,
        )
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

    def create(
        self,
        name: str,
        filename: str,
        rows: int,
        columns: int,
        sku_count: int,
        quality_score: float,
        date_from: str,
        date_to: str,
        owner: str,
        import_batch_id: str = None,
    ) -> Dataset:
        ds = Dataset(
            name=name,
            filename=filename,
            rows=rows,
            columns=columns,
            sku_count=sku_count,
            quality_score=quality_score,
            date_from=date_from,
            date_to=date_to,
            owner=owner,
            import_batch_id=import_batch_id,
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

    def save(
        self,
        sku: str,
        model_name: str,
        horizon: int,
        total_forecast: float,
        mae: float,
        rmse: float,
        mape: float,
        dataset_id: int = None,
    ) -> ForecastRun:
        run = ForecastRun(
            sku=sku,
            model_name=model_name,
            horizon=horizon,
            total_forecast=total_forecast,
            mae=mae,
            rmse=rmse,
            mape=mape,
            dataset_id=dataset_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_by_sku(self, sku: str) -> List[ForecastRun]:
        return (
            self.db.query(ForecastRun)
            .filter(ForecastRun.sku == sku)
            .order_by(ForecastRun.created_at.desc())
            .all()
        )

    def get_latest(self, sku: str) -> Optional[ForecastRun]:
        return (
            self.db.query(ForecastRun)
            .filter(ForecastRun.sku == sku)
            .order_by(ForecastRun.created_at.desc())
            .first()
        )


# ── Training Run Repository ───────────────────────────────────────────────────
class TrainingRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        sku: str,
        model_name: str,
        rmse: float,
        mae: float,
        mape: float,
        samples: int,
        features: int,
        model_path: str,
        dataset_id: int = None,
    ) -> TrainingRun:
        run = TrainingRun(
            sku=sku,
            model_name=model_name,
            rmse=rmse,
            mae=mae,
            mape=mape,
            samples=samples,
            features=features,
            model_path=model_path,
            dataset_id=dataset_id,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def save_training_run(
        self,
        sku: str,
        model_name: str,
        rmse: float,
        mae: float,
        mape: float,
        samples: int,
        features: int,
        model_path: str = None,
        dataset_id: int = None,
        winner: bool = False,
        forecast_horizon: int = 30,
        sample_count: int = None,
        timestamp: datetime = None,
    ) -> TrainingRun:
        from datetime import datetime
        run = TrainingRun(
            sku=sku,
            model_name=model_name,
            rmse=rmse,
            mae=mae,
            mape=mape,
            samples=samples,
            features=features,
            model_path=model_path,
            dataset_id=dataset_id,
            winner=winner,
            forecast_horizon=forecast_horizon,
            sample_count=sample_count if sample_count is not None else samples,
            timestamp=timestamp or datetime.utcnow(),
            trained_at=timestamp or datetime.utcnow(),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def _get_latest_dataset_id(self) -> Optional[int]:
        from backend.database.models import Dataset
        latest_ds = self.db.query(Dataset).order_by(Dataset.uploaded_at.desc()).first()
        return latest_ds.id if latest_ds else None

    def get_training_history(self, limit: int = 100) -> List[TrainingRun]:
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        return (
            query.order_by(TrainingRun.trained_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_training_run(self, sku: str) -> Optional[TrainingRun]:
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun).filter(TrainingRun.sku == sku)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        return (
            query.order_by(TrainingRun.trained_at.desc())
            .first()
        )

    def get_model_win_frequency(self) -> dict[str, int]:
        from sqlalchemy import func
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun.model_name, func.count(TrainingRun.id)).filter(TrainingRun.winner == True)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        results = query.group_by(TrainingRun.model_name).all()
        return {name: count for name, count in results}

    def get_rmse_trend(self, limit: int = 50) -> list[dict]:
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun).filter(TrainingRun.winner == True)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        runs = (
            query.order_by(TrainingRun.trained_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "timestamp": (r.timestamp or r.trained_at).isoformat() if (r.timestamp or r.trained_at) else None,
                "sku": r.sku,
                "model_name": r.model_name,
                "rmse": r.rmse,
                "mae": r.mae,
                "mape": r.mape
            }
            for r in runs
        ]

    def get_mape_trend(self, limit: int = 50) -> list[dict]:
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun).filter(TrainingRun.winner == True)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        runs = (
            query.order_by(TrainingRun.trained_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "timestamp": (r.timestamp or r.trained_at).isoformat() if (r.timestamp or r.trained_at) else None,
                "sku": r.sku,
                "model_name": r.model_name,
                "rmse": r.rmse,
                "mae": r.mae,
                "mape": r.mape
            }
            for r in runs
        ]


    def leaderboard(self, dataset_id: Optional[int] = None) -> List[TrainingRun]:
        target_id = dataset_id if dataset_id is not None else self._get_latest_dataset_id()
        query = self.db.query(TrainingRun)
        if target_id is not None:
            query = query.filter(TrainingRun.dataset_id == target_id)
        return query.order_by(TrainingRun.rmse).all()

    def get_by_sku(self, sku: str) -> List[TrainingRun]:
        latest_id = self._get_latest_dataset_id()
        query = self.db.query(TrainingRun).filter(TrainingRun.sku == sku)
        if latest_id is not None:
            query = query.filter(TrainingRun.dataset_id == latest_id)
        return (
            query.order_by(TrainingRun.trained_at.desc())
            .all()
        )

    def get_accuracy_summary(self) -> dict:
        from sqlalchemy import func
        latest_id = self._get_latest_dataset_id()
        
        total_query = self.db.query(func.count(TrainingRun.id))
        winner_query = self.db.query(TrainingRun).filter(TrainingRun.winner == True)
        
        if latest_id is not None:
            total_query = total_query.filter(TrainingRun.dataset_id == latest_id)
            winner_query = winner_query.filter(TrainingRun.dataset_id == latest_id)
            
        total_runs = total_query.scalar() or 0
        winning_runs = winner_query.all()
        
        win_freq = self.get_model_win_frequency()
        
        avg_rmse = 0.0
        avg_mape = 0.0
        if winning_runs:
            avg_rmse = sum(r.rmse for r in winning_runs if r.rmse is not None) / len(winning_runs)
            avg_mape = sum(r.mape for r in winning_runs if r.mape is not None) / len(winning_runs)
            
        perf_query = self.db.query(TrainingRun.model_name, func.avg(TrainingRun.rmse))
        if latest_id is not None:
            perf_query = perf_query.filter(TrainingRun.dataset_id == latest_id)
        model_perf = perf_query.group_by(TrainingRun.model_name).all()
        model_perf = [(m, float(r)) for m, r in model_perf if r is not None]
        
        best_model = None
        worst_model = None
        if model_perf:
            best_model = min(model_perf, key=lambda x: x[1])[0]
            worst_model = max(model_perf, key=lambda x: x[1])[0]
            
        sku_query = self.db.query(TrainingRun.sku, func.avg(TrainingRun.rmse)).filter(TrainingRun.winner == True)
        if latest_id is not None:
            sku_query = sku_query.filter(TrainingRun.dataset_id == latest_id)
        sku_perf = sku_query.group_by(TrainingRun.sku).all()
        sku_perf = [(s, float(r)) for s, r in sku_perf if r is not None]
        
        best_sku = None
        worst_sku = None
        if sku_perf:
            best_sku = min(sku_perf, key=lambda x: x[1])[0]
            worst_sku = max(sku_perf, key=lambda x: x[1])[0]
            
        ts_query = self.db.query(func.max(TrainingRun.trained_at))
        if latest_id is not None:
            ts_query = ts_query.filter(TrainingRun.dataset_id == latest_id)
        last_run = ts_query.scalar()
        last_timestamp = last_run.isoformat() if last_run else None
        
        return {
            "avg_rmse": round(avg_rmse, 3),
            "avg_mape": round(avg_mape, 3),
            "total_runs": total_runs,
            "last_retraining_timestamp": last_timestamp,
            "best_performing_model": best_model,
            "worst_performing_model": worst_model,
            "best_sku": best_sku,
            "worst_sku": worst_sku,
            "model_wins": win_freq
        }

    def get_sku_performance(self) -> list[dict]:
        from sqlalchemy import func
        latest_id = self._get_latest_dataset_id()
        
        sku_query = self.db.query(TrainingRun.sku).distinct()
        if latest_id is not None:
            sku_query = sku_query.filter(TrainingRun.dataset_id == latest_id)
        skus = sku_query.all()
        skus = [s[0] for s in skus]
        
        results = []
        for sku in skus:
            total_query = self.db.query(func.count(TrainingRun.id)).filter(TrainingRun.sku == sku)
            winner_query = self.db.query(TrainingRun).filter(TrainingRun.sku == sku, TrainingRun.winner == True)
            
            if latest_id is not None:
                total_query = total_query.filter(TrainingRun.dataset_id == latest_id)
                winner_query = winner_query.filter(TrainingRun.dataset_id == latest_id)
                
            total_evals = total_query.scalar() or 0
            latest_winner = winner_query.order_by(TrainingRun.trained_at.desc()).first()
            
            if latest_winner:
                results.append({
                    "sku": sku,
                    "latest_model": latest_winner.model_name,
                    "rmse": latest_winner.rmse,
                    "mape": latest_winner.mape,
                    "total_evaluations": total_evals,
                    "timestamp": (latest_winner.timestamp or latest_winner.trained_at).isoformat()
                })
            else:
                any_query = self.db.query(TrainingRun).filter(TrainingRun.sku == sku)
                if latest_id is not None:
                    any_query = any_query.filter(TrainingRun.dataset_id == latest_id)
                latest_any = any_query.order_by(TrainingRun.trained_at.desc()).first()
                if latest_any:
                    results.append({
                        "sku": sku,
                        "latest_model": latest_any.model_name,
                        "rmse": latest_any.rmse,
                        "mape": latest_any.mape,
                        "total_evaluations": total_evals,
                        "timestamp": (latest_any.timestamp or latest_any.trained_at).isoformat()
                    })
        return results


# ── Simulation Repository ─────────────────────────────────────────────────────
class SimulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        sku: str,
        scenario_name: str,
        baseline_forecast: float,
        simulated_demand: float,
        revenue: float,
        profit: float,
        stockout_risk: str,
        inventory_gap: float,
        params: dict,
    ) -> SimulationRun:
        run = SimulationRun(
            sku=sku,
            scenario_name=scenario_name,
            baseline_forecast=baseline_forecast,
            simulated_demand=simulated_demand,
            revenue=revenue,
            profit=profit,
            stockout_risk=stockout_risk,
            inventory_gap=inventory_gap,
            params=params,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_recent(self, limit: int = 20) -> List[SimulationRun]:
        return (
            self.db.query(SimulationRun)
            .order_by(SimulationRun.created_at.desc())
            .limit(limit)
            .all()
        )


# ── Audit Repository ──────────────────────────────────────────────────────────
class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        user: str,
        action: str,
        resource: str,
        detail: str = "",
        ip_address: str = "",
    ) -> AuditLog:
        entry = AuditLog(
            user=user,
            action=action,
            resource=resource,
            detail=detail,
            ip_address=ip_address,
        )
        self.db.add(entry)
        self.db.commit()
        return entry

    def get_recent(self, limit: int = 50) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .all()
        )

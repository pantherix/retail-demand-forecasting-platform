from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import importlib
import logging
import os
import traceback
from contextlib import asynccontextmanager

# --- Monitoring & APM Integrations ---
# Make optional integrations not required for the service to boot.
try:
    import sentry_sdk  # pyright: ignore[reportMissingImports]
    from sentry_sdk.integrations.fastapi import (  # pyright: ignore[reportMissingImports]
        FastApiIntegration,
    )
except ModuleNotFoundError:  # pragma: no cover
    sentry_sdk = None
    FastApiIntegration = None

try:
    _prometheus_module = importlib.import_module("prometheus_fastapi_instrumentator")
    Instrumentator = getattr(_prometheus_module, "Instrumentator", None)
except (ModuleNotFoundError, ImportError):  # pragma: no cover
    Instrumentator = None


from backend.api.enterprise import router as enterprise_router
from backend.api.ws import router as ws_router
from fastapi import Depends, FastAPI  # pyright: ignore[reportMissingImports]
from fastapi.middleware.cors import (  # pyright: ignore[reportMissingImports]
    CORSMiddleware,
)  # pyright: ignore[reportMissingImports]
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.auth import router as auth_router
from backend.api.copilot import router as copilot_router
from backend.api.dataset import router as dataset_router
from backend.api.executive import router as executive_router

# --- API Route Imports ---
from backend.api.forecast import router as forecast_router
from backend.api.intelligence import router as intelligence_router
from backend.api.inventory import router as inventory_router
from backend.api.leaderboard import router as leaderboard_router
from backend.api.reports import router as reports_router
from backend.api.risk import router as risk_router
from backend.api.simulation import router as simulation_router
from backend.api.training import router as training_router
from backend.database.session import get_db

# NOTE: Risk/stockout/ranking logic in this file is implemented as a SQLAlchemy
# background worker. Pylance may flag round()/bool checks as type issues because
# SQLAlchemy column expressions are not real Python scalars. These are runtime
# safe because all values used in round() are explicitly converted to Python
# floats/ints after .scalar() / numeric calculations.


# Initialize Logging
import json
import logging.config

# Structured JSON logging configuration
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(message)s",
            "class": "logging.Formatter",
            "style": "%",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": "INFO",
        }
    },
    "loggers": {
        "retailgpt.backend": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger("retailgpt.backend")

# Initialize Sentry APM if DSN exists (and sentry_sdk is installed)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if (
    sentry_sdk is not None
    and FastApiIntegration is not None
    and SENTRY_DSN
    and SENTRY_DSN.lower() != "none"
):
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,  # Profile 10% of traffic paths
        profiles_sample_rate=0.1,
    )
    logger.info("APM Tracking Engine: Sentry initialized")


def start_predictive_runout_worker():
    import threading
    import time

    from backend.database.session import SessionLocal

    def run_worker():
        logger.info(
            "Background Worker Engine: Started predictive runout calculations thread"
        )
        while True:
            try:
                from datetime import datetime, timedelta

                from sqlalchemy import func

                from backend.database.models import (
                    Forecast,
                    InventoryItem,
                    Product,
                    RiskScore,
                    Sale,
                )

                db = SessionLocal()
                try:
                    # Bulk Aggregations to avoid N+1 query vulnerability that blocks the GIL
                    from datetime import datetime, timedelta
                    from sqlalchemy import func

                    # 1. Fetch total stock per product
                    stock_sums = dict(
                        db.query(InventoryItem.product_id, func.sum(InventoryItem.current_stock))
                        .group_by(InventoryItem.product_id)
                        .all()
                    )

                    # 2. Fetch sales sum per product in last 30 days
                    cutoff_date = datetime.utcnow() - timedelta(days=30)
                    sales_sums = dict(
                        db.query(Sale.product_id, func.sum(Sale.quantity))
                        .filter(Sale.transaction_date >= cutoff_date)
                        .group_by(Sale.product_id)
                        .all()
                    )

                    # 3. Fetch forecast expected demand sum per product in future
                    now = datetime.utcnow()
                    forecast_sums = dict(
                        db.query(Forecast.product_id, func.sum(Forecast.expected_demand))
                        .filter(Forecast.forecast_date > now)
                        .group_by(Forecast.product_id)
                        .all()
                    )

                    # 4. Fetch all existing risk scores by product_id
                    risk_scores = {r.product_id: r for r in db.query(RiskScore).all()}

                    # 5. Fetch all products
                    products = db.query(Product).all()

                    def as_float(value: object | None, default: float = 0.0) -> float:
                        try:
                            return float(value)  # type: ignore[arg-type]
                        except (TypeError, ValueError):
                            return default

                    for prod in products:
                        # 1. Total Stock (from pre-fetched map)
                        tot_stock = float(stock_sums.get(prod.id) or 0.0)

                        # 2. Average Daily Sales (from pre-fetched map)
                        sales_sum = float(sales_sums.get(prod.id) or 0.0)
                        avg_daily = sales_sum / 30.0

                        if avg_daily <= 0:
                            f_sum = float(forecast_sums.get(prod.id) or 0.0)
                            avg_daily = f_sum / 30.0

                        # Days of Cover = Stock / Max(Average Daily Sales, 0.001)
                        avg_daily_safe = max(avg_daily, 0.001)
                        days_of_cover = tot_stock / avg_daily_safe

                        lead_time = prod.lead_time_days or (
                            prod.supplier.lead_time_days if prod.supplier else 7
                        )
                        if not isinstance(lead_time, (int, float, str)):
                            lead_time = 7.0
                        else:
                            try:
                                lead_time = float(lead_time)
                            except (TypeError, ValueError):
                                lead_time = 7.0
                        if lead_time <= 0:
                            lead_time = 7.0

                        # Determine priority and actions
                        shortage_qty = max(
                            0.0, (avg_daily_safe * lead_time) - tot_stock
                        )
                        base_price = as_float(prod.base_price)
                        unit_cost = as_float(prod.unit_cost)
                        rev_at_risk = shortage_qty * base_price
                        prof_at_risk = shortage_qty * (base_price - unit_cost)
                        if days_of_cover < lead_time:
                            action: str = "Order Now"
                            priority: int = 1 if days_of_cover < 3 else 2
                            urgency: float = max(
                                0.0, min(1.0, 1.0 - (days_of_cover / lead_time))
                            )
                            root_causes: list[str] = [
                                f"Low Days of Cover ({days_of_cover:.1f}d < {lead_time}d)"
                            ]
                            reorder_qty: float = max(10.0, shortage_qty * 2.0)
                        else:
                            action = "Monitor"
                            priority = 4
                            urgency = 0.15
                            root_causes = ["Stock levels healthy"]
                            reorder_qty = 0.0
                            rev_at_risk = 0.0
                            prof_at_risk = 0.0

                        risk = risk_scores.get(prod.id)
                        if not risk:
                            risk = RiskScore(
                                product_id=prod.id,
                                revenue_at_risk=float(round(float(rev_at_risk), 2)),
                                profit_at_risk=float(round(float(prof_at_risk), 2)),
                                financial_priority=int(priority),  # type: ignore[arg-type]
                                forecast_confidence=85.0,
                                expected_stockout_days=float(
                                    round(max(0.0, lead_time - days_of_cover), 1)
                                    if days_of_cover < lead_time
                                    else 0.0
                                ),
                                recommended_action=action,  # type: ignore[arg-type]
                                urgency=float(urgency),  # type: ignore[arg-type]
                                root_causes=root_causes,  # type: ignore[arg-type]
                                service_level=95.0,
                                reorder_quantity=float(round(float(reorder_qty), 1)),
                                status="Open",
                            )
                            db.add(risk)
                        else:
                            if (
                                risk.status not in ["Open", "In Progress"]
                                and rev_at_risk > 0
                            ):
                                risk.status = "Open"
                            if risk.status in ["Open", "In Progress"]:
                                risk.revenue_at_risk = round(
                                    float(rev_at_risk), 2
                                )  # pyright: ignore[reportAttributeAccessIssue]
                                risk.profit_at_risk = round(
                                    float(prof_at_risk), 2
                                )  # pyright: ignore[reportAttributeAccessIssue]
                                risk.financial_priority = priority
                                risk.expected_stockout_days = (
                                    round(max(0.0, float(lead_time) - days_of_cover), 1)
                                    if days_of_cover < lead_time
                                    else 0.0
                                )
                                risk.recommended_action = action
                                risk.urgency = urgency
                                risk.root_causes = root_causes
                                risk.reorder_quantity = round(float(reorder_qty), 1)
                    db.commit()
                except Exception as db_err:
                    db.rollback()
                    logger.error(f"Background Worker Engine DB Error: {db_err}")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Background Worker Engine execution loop failed: {e}")

            worker_interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "30"))
            time.sleep(worker_interval)

    t = threading.Thread(target=run_worker, daemon=True)
    t.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the continuous background thread worker
    start_predictive_runout_worker()

    fail_on_db_init = os.getenv("FAIL_ON_DB_INIT", "0").lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    enable_seed_data = os.getenv("ENABLE_SEED_DATA", "0") == "1"

    try:
        from backend.database.session import create_tables
        from sqlalchemy.exc import SQLAlchemyError

        logger.info(json.dumps({"event": "db_init_start", "message": "Starting database initialization"}))
        try:
            create_tables()
            logger.info(json.dumps({"event": "db_tables_verified", "status": "success", "message": "Database tables verified and ready"}))

            if enable_seed_data:
                from backend.database.seed_db import seed_all

                seed_all()
                logger.info(json.dumps({"event": "db_seed_completed", "status": "success", "message": "Database seed validation completed"}))
            else:
                logger.info(json.dumps({"event": "db_seed_skipped", "status": "skipped", "message": "Database seeding skipped (ENABLE_SEED_DATA=0)"}))

        except SQLAlchemyError as sql_err:
            logger.error(json.dumps({
                "event": "db_init_sql_error",
                "status": "error",
                "error_type": "SQLAlchemyError",
                "error": str(sql_err),
                "traceback": traceback.format_exc()
            }))
            if fail_on_db_init:
                raise
        except Exception as init_err:
            logger.error(json.dumps({
                "event": "db_init_unexpected_error",
                "status": "error",
                "error_type": type(init_err).__name__,
                "error": str(init_err),
                "traceback": traceback.format_exc()
            }))
            if fail_on_db_init:
                raise
    except Exception as e:
        logger.error(json.dumps({
            "event": "db_init_boot_sequence_critical",
            "status": "critical",
            "fail_on_db_init": fail_on_db_init,
            "error": str(e),
            "traceback": traceback.format_exc()
        }))
        if fail_on_db_init:
            raise e
    yield


app = FastAPI(
    title="RetailGPT Enterprise",
    version="2.0.0",
    description="Retail Demand Intelligence Platform — Forecasting · Risk · Simulation · AI Copilot",
    lifespan=lifespan,
)

# Hardened CORS Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Expose Prometheus Telemetry Scraping Layer ---
if Instrumentator is not None and os.getenv(
    "PROMETHEUS_METRICS_ENABLED", "true"
).lower() in {"1", "true", "yes"}:
    # mypy/pyright/pylance can’t infer this optional type reliably
    _instrumentator = Instrumentator()  # type: ignore[operator]
    _instrumentator.instrument(app).expose(app, endpoint="/metrics")
    logger.info("Telemetry Engine: Metrics scraping exposed at /metrics")

# --- App Routers Registration ---
app.include_router(auth_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")
app.include_router(executive_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(intelligence_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(enterprise_router, prefix="/api/enterprise", tags=["Enterprise"])
app.include_router(ws_router, prefix="/api")


@app.get("/")
def root():
    return {
        "project": "RetailGPT Enterprise",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/health")
def api_health(db: Session = Depends(get_db)):
    import tempfile
    from pathlib import Path

    from sqlalchemy import text

    from backend.database.models import Forecast

    # 1. Database Connectivity Validation
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        logger.error(f"Health Check: Database connection failed: {e}")

    if not db_healthy:
        return {
            "status": "red",
            "details": {
                "database": "down",
                "ingestion": "unknown",
                "copilot": "unknown",
                "forecast_engine": "unknown",
            },
        }

    # 2. Disk Storage / Ingestion Subsystem Validation
    ingestion_healthy = False
    try:
        upload_dir = Path(__file__).resolve().parent / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_file = tempfile.NamedTemporaryFile(dir=upload_dir, delete=False)
        temp_file.close()
        os.unlink(temp_file.name)
        ingestion_healthy = True
    except Exception as e:
        logger.error(f"Health Check: Ingestion directory not writable: {e}")

    # 3. Copilot Provider Check
    provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    llm_configured = False
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "")
        if key and key != "your-openai-key-here":
            llm_configured = True
    elif provider == "groq":
        key = os.getenv("GROQ_API_KEY", "")
        if key:
            llm_configured = True
    elif provider == "ollama":
        llm_configured = True

    # 4. Forecast Evaluation
    forecasts_exist = False
    try:
        forecast_count = db.query(Forecast).count()
        if forecast_count > 0:
            forecasts_exist = True
    except Exception as e:
        logger.error(f"Health Check: Forecast verification step failed: {e}")

    # Aggregate Health Scoring
    if not ingestion_healthy or not llm_configured or not forecasts_exist:
        status = "yellow"
    else:
        status = "green"

    return {
        "status": status,
        "details": {
            "database": "healthy",
            "ingestion": "healthy" if ingestion_healthy else "error",
            "copilot": "configured" if llm_configured else "missing_keys",
            "forecast_engine": "active" if forecasts_exist else "empty",
        },
    }

@app.post("/api/reset_telemetry")
def reset_telemetry():
    """Reset in-memory Prometheus telemetry metrics to zero."""
    try:
        from prometheus_client import REGISTRY
        collectors = list(REGISTRY._collector_to_names.keys())
        cleared = 0
        for collector in collectors:
            try:
                REGISTRY.unregister(collector)
                cleared += 1
            except Exception:
                pass
        logger.info(f"Telemetry reset: {cleared} collector(s) cleared.")
        return {"status": "ok", "cleared": cleared}
    except ImportError:
        return {"status": "ok", "cleared": 0, "detail": "prometheus_client not installed"}
    except Exception as e:
        logger.error(f"Failed to reset telemetry: {e}")
        return {"status": "error", "detail": str(e)}

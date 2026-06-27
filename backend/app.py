from __future__ import annotations

import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.forecast import router as forecast_router
from api.inventory import router as inventory_router
from api.copilot import router as copilot_router
from api.simulation import router as simulation_router
from api.executive import router as executive_router
from api.risk import router as risk_router
from api.reports import router as reports_router
from api.auth import router as auth_router
from api.dataset import router as dataset_router
from api.leaderboard import router as leaderboard_router
from api.intelligence import router as intelligence_router
from api.enterprise import router as enterprise_router

logger = logging.getLogger("retailgpt.backend")
if not logger.handlers:
    # Keep it simple and cross-platform: if the host app configures logging,
    # this won't duplicate handlers.
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    fail_on_db_init = os.getenv("FAIL_ON_DB_INIT", "0").lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    try:
        from database.session import create_tables

        create_tables()
        logger.info("Database tables ready")

        from database.seed_db import seed_all

        seed_all()
        logger.info("Database seed completed")
    except Exception:
        # Use full traceback so DB initialization issues are not silent.
        logger.exception(
            "DB init skipped (startup best-effort). FAIL_ON_DB_INIT=%s",
            os.getenv("FAIL_ON_DB_INIT", "0"),
        )
        logger.error(traceback.format_exc())

        if fail_on_db_init:
            raise

    yield


app = FastAPI(
    title="RetailGPT Enterprise",
    version="2.0.0",
    description="Retail Demand Intelligence Platform — Forecasting · Risk · Simulation · AI Copilot",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
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
app.include_router(enterprise_router, prefix="/api")


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
def api_health():
    from database.session import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_status = "connected"
        status = "green"
    except Exception as e:
        db_status = f"error: {str(e)}"
        status = "red"
    finally:
        db.close()
    return {
        "status": status,
        "details": {
            "database": db_status
        }
    }


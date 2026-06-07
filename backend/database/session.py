from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/retailgpt",
)

# SQLite fallback for local dev without Postgres
_USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
if _USE_SQLITE:
    DATABASE_URL = "sqlite:///./retailgpt.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables. Called at startup."""
    from database.models import Base as BaseModels
    from database.intelligence import Base as IntelligenceBase
    BaseModels.metadata.create_all(bind=engine)
    IntelligenceBase.metadata.create_all(bind=engine)

from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
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
    import sys
    is_testing = ("pytest" in sys.modules) or os.getenv("TESTING", "false").lower() == "true"
    db_name = "retailgpt_test.db" if is_testing else "retailgpt.db"
    _db_path = os.path.abspath(f"./{db_name}")
    DATABASE_URL = f"sqlite:///{_db_path}"
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


def create_tables() -> None:
    """Create all tables based on current SQLAlchemy models."""
    from backend.database.models import Base as BaseModels
    from backend.database.intelligence import Base as IntelligenceBase
    BaseModels.metadata.create_all(bind=engine)
    IntelligenceBase.metadata.create_all(bind=engine)

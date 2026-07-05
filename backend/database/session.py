from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

load_dotenv(find_dotenv())
logger = logging.getLogger("retailgpt.backend")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/retailgpt",
)

_USE_SQLITE = (
    os.getenv("USE_SQLITE", "false").lower() == "true"
    or "sqlite" in DATABASE_URL.lower()
)

if _USE_SQLITE:
    # Explicit safe path calculation regardless of calling context depth
    ROOT_DIR = Path(__file__).resolve().parent
    while ROOT_DIR.name and ROOT_DIR.name != "backend" and ROOT_DIR.parent != ROOT_DIR:
        ROOT_DIR = ROOT_DIR.parent

    import sys
    is_testing = (
        "pytest" in sys.modules
        or os.getenv("TESTING", "false").lower() == "true"
        or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
    )
    db_name = "retailgpt_test.db" if is_testing else "retailgpt.db"

    # Place the database file cleanly inside the root app execution zone
    db_path = (ROOT_DIR.parent / db_name).resolve()
    DATABASE_URL = f"sqlite:///{db_path.as_posix()}"

    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },  # Avoid instant lockouts during busy loops
    )

    # Enable WAL mode + foreign key enforcement on connection activation
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception as e:
            logger.warning(f"Failed to apply optimization pragmas: {e}")
        finally:
            cursor.close()

else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,  # Expanded pool capacity for higher concurrency
        max_overflow=20,  # Flex cap during data ingestion operations
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_lineage_columns(engine):
    from sqlalchemy import inspect

    inspector = inspect(engine)

    columns_to_add = [
        ("import_batch_id", "VARCHAR(100)"),
        ("source_type", "VARCHAR(50)"),
        ("source_file", "VARCHAR(255)"),
        ("import_timestamp", "TIMESTAMP"),
        ("created_by_import", "BOOLEAN"),
    ]
    tables = [
        "products",
        "inventory",
        "sales",
        "forecasts_new",
        "risk_scores",
        "alerts",
        "datasets",
    ]
    is_sqlite = "sqlite" in str(engine.url)

    with engine.begin() as conn:
        for table in tables:
            if not inspector.has_table(table):
                continue
            existing_columns = {col["name"] for col in inspector.get_columns(table)}
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    if col_name == "created_by_import":
                        actual_type = (
                            "BOOLEAN DEFAULT 0"
                            if is_sqlite
                            else "BOOLEAN DEFAULT FALSE"
                        )
                    else:
                        actual_type = col_type
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE {table} ADD COLUMN {col_name} {actual_type}"
                            )
                        )
                        logger.info(
                            f"Migration: Added column {col_name} to table {table}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Migration Failed: Column {col_name} on table {table}: {e}"
                        )

        # Migrate training_runs columns if missing
        if inspector.has_table("training_runs"):
            existing_tr_cols = {col["name"] for col in inspector.get_columns("training_runs")}
            tr_migrations = [
                ("winner", "BOOLEAN DEFAULT 0" if is_sqlite else "BOOLEAN DEFAULT FALSE"),
                ("forecast_horizon", "INTEGER"),
                ("sample_count", "INTEGER"),
                ("timestamp", "TIMESTAMP"),
            ]
            for col_name, col_type in tr_migrations:
                if col_name not in existing_tr_cols:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE training_runs ADD COLUMN {col_name} {col_type}"
                            )
                        )
                        logger.info(
                            f"Migration: Added column {col_name} to training_runs"
                        )
                    except Exception as e:
                        logger.error(
                            f"Migration Failed: Column {col_name} on table training_runs: {e}"
                        )


def create_tables():
    """Create all tables and run runtime lineage updates."""
    from backend.database.intelligence import Base as IntelligenceBase
    from backend.database.models import Base as BaseModels
    from backend.database.import_task import ImportTask  # Register ImportTask model

    BaseModels.metadata.create_all(bind=engine)
    IntelligenceBase.metadata.create_all(bind=engine)
    migrate_lineage_columns(engine)

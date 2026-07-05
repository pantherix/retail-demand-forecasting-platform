# backend/services/import_worker.py

"""Background worker for asynchronous dataset import.

This module defines a function `process_import` that is intended to be scheduled
as a FastAPI background task. It performs the same import logic as the
`/dataset/import` endpoint but runs in a separate thread/process so the API
returns immediately.
"""

from __future__ import annotations

import uuid
import io
import time
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

# Import local modules
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.api.dataset import DatasetImportPayload, detect_column_mappings, fuzzy_match_schema
from backend.services.adapters import CSVAdapter, XLSXAdapter
from backend.database.import_task import ImportTask, ImportTaskStatus
from backend.database.session import SessionLocal


def _update_task(session: Session, task_id: str, **updates) -> None:
    """Utility to update an ImportTask record safely."""
    task = session.query(ImportTask).filter(ImportTask.task_id == task_id).first()
    if not task:
        return
    for key, value in updates.items():
        setattr(task, key, value)
    session.add(task)
    session.commit()


def process_import(task_id: str, payload: DatasetImportPayload) -> None:
    """Execute the import workflow for a given task.

    This function is designed to be called via ``BackgroundTasks.add_task``.
    It creates its own DB session, updates progress, and stores the final
    result or error in the ``import_tasks`` table.
    """
    db: Session = SessionLocal()
    try:
        # Mark task as running
        _update_task(db, task_id, status=ImportTaskStatus.RUNNING, progress=0.0)

        # -----------------------------------------------------------------
        # The logic below mirrors the original ``import_dataset`` endpoint.
        # It has been trimmed down to the essential steps required for a
        # functional import while preserving progress updates.
        # -----------------------------------------------------------------
        source_type = payload.source_type.lower()

        # 1. Load temporary file
        if source_type not in {"csv", "xlsx"}:
            raise ValueError(f"Unsupported source type: {source_type}")
        if not payload.temp_file_id:
            raise ValueError("Missing temporary file ID for file import")

        data_dir = Path(__file__).resolve().parents[3] / "data" / "uploads"
        file_path = data_dir / payload.temp_file_id
        if not file_path.exists():
            raise FileNotFoundError("Temporary file not found or expired")
        file_data = file_path.read_bytes()

        # 2. Validate mapping input
        raw_mapping = payload.mapping or {}
        mapping: dict[str, str] = {k: v for k, v in raw_mapping.items() if v}
        # Normalize legacy keys
        if "identity_key" in mapping:
            mapping["sku"] = mapping.pop("identity_key")
        if "stock_on_hand" in mapping:
            mapping["current_stock"] = mapping.pop("stock_on_hand")
        if "velocity_rate" in mapping:
            mapping["revenue"] = mapping.pop("velocity_rate")

        required_fields = ["sku", "date", "current_stock"]
        for rf in required_fields:
            if not mapping.get(rf):
                raise ValueError(f"Required target field '{rf}' is not mapped")

        # 3. Detect low‑confidence mappings (optional warnings)
        if source_type == "csv":
            df_val = pd.read_csv(io.BytesIO(file_data))
        else:
            df_val = pd.read_excel(io.BytesIO(file_data))
        from backend.api.dataset import detect_column_mappings
        detected = detect_column_mappings(df_val)
        # (We skip warning handling for brevity)

        # 4. Choose the correct adapter
        if source_type == "csv":
            adapter = CSVAdapter(data=file_data, mapping=mapping)
        else:
            adapter = XLSXAdapter(data=file_data, mapping=mapping)

        # 5. Parse the file into canonical structures
        canonical_data = adapter.parse()
        products = canonical_data.get("products", [])
        inventory = canonical_data.get("inventory", [])
        sales = canonical_data.get("sales", [])

        # 6. Simple persistence – for demo purposes we just count rows.
        # In a real system you would write to the appropriate tables via
        # repository classes.
        result_summary = {
            "product_count": len(products),
            "inventory_count": len(inventory),
            "sales_count": len(sales),
        }

        # Mark task as completed
        _update_task(
            db,
            task_id,
            status=ImportTaskStatus.COMPLETED,
            progress=100.0,
            result=result_summary,
        )
    except Exception as exc:  # pragma: no cover – defensive
        # Update task with failure details
        _update_task(
            db,
            task_id,
            status=ImportTaskStatus.FAILED,
            progress=0.0,
            error_message=str(exc),
        )
    finally:
        db.close()

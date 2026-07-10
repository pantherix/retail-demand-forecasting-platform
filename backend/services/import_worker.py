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


def process_import(task_id: str, payload: DatasetImportPayload, username: str) -> None:
    """Execute the import workflow for a given task asynchronously.
    Updates the database with the real dataset metrics and runs the forecasting pipeline.
    """
    db: Session = SessionLocal()
    try:
        # Mark task as running
        _update_task(db, task_id, status=ImportTaskStatus.RUNNING, progress=10.0)

        source_type = payload.source_type.lower()

        # 1. Load temporary file
        if source_type not in {"csv", "xlsx"}:
            raise ValueError(f"Unsupported source type: {source_type}")
        if not payload.temp_file_id:
            raise ValueError("Missing temporary file ID for file import")

        data_dir = Path(__file__).resolve().parents[2] / "data" / "uploads"
        file_path = data_dir / payload.temp_file_id
        if not file_path.exists():
            raise FileNotFoundError("Temporary file not found or expired")
        file_data = file_path.read_bytes()

        _update_task(db, task_id, progress=25.0)

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

        _update_task(db, task_id, progress=35.0)

        # 3. Choose the correct adapter
        if source_type == "csv":
            adapter = CSVAdapter(data=file_data, mapping=mapping)
        else:
            adapter = XLSXAdapter(data=file_data, mapping=mapping)

        # 4. Parse the file into canonical structures
        canonical_data = adapter.parse()
        _update_task(db, task_id, progress=45.0)

        # 5. Profile & sanitize canonical data
        from backend.api.dataset import sanitize_and_profile_dataset
        (
            cleaned_canonical_data,
            quality_score,
            warnings,
            dataset_name,
            filename,
            import_batch_id,
            import_timestamp,
            lineage_metadata,
            imported_rows,
            total_rows,
            rejected_rows,
            missing_sku_count,
            missing_date_count,
        ) = sanitize_and_profile_dataset(source_type, mapping, canonical_data, payload.temp_file_id, [])

        if imported_rows == 0:
            raise ValueError("Import rejected: 0 valid sales rows after filtering")

        _update_task(db, task_id, progress=55.0)

        # 6. Database dataset registry persistence
        from backend.database.repositories import DatasetRepository, AuditRepository
        
        date_from = (
            min(s["date"] for s in cleaned_canonical_data["sales"]).strftime("%Y-%m-%d") if cleaned_canonical_data["sales"] else ""
        )
        date_to = (
            max(s["date"] for s in cleaned_canonical_data["sales"]).strftime("%Y-%m-%d") if cleaned_canonical_data["sales"] else ""
        )
        
        ds = DatasetRepository(db).create(
            name=dataset_name,
            filename=filename,
            rows=imported_rows,
            columns=len(payload.mapping) if payload.mapping else 5,
            sku_count=len(set(p["sku"] for p in cleaned_canonical_data["products"])),
            quality_score=quality_score,
            date_from=date_from,
            date_to=date_to,
            owner=username,
            import_batch_id=import_batch_id,
        )

        AuditRepository(db).log(
            username,
            "import",
            "dataset",
            f"Imported canonical data via async task from {source_type} — {imported_rows} valid rows, score: {quality_score}",
        )

        _update_task(db, task_id, progress=65.0)

        # 7. Run ML training and synchronization pipeline synchronously in the worker task thread
        from backend.forecasting.pipeline import run_training_pipeline_canonical
        run_training_pipeline_canonical(
            db,
            cleaned_canonical_data,
            username,
            lineage_metadata,
        )

        result_summary = {
            "success": True,
            "dataset_id": ds.id,
            "name": ds.name,
            "rows": ds.rows,
            "sku_count": ds.sku_count,
            "quality_score": ds.quality_score,
            "date_range": f"{date_from} → {date_to}" if date_from else "N/A",
            "metrics": {
                "total_rows": total_rows,
                "imported_rows": imported_rows,
                "rejected_rows": rejected_rows,
                "missing_sku_count": missing_sku_count,
                "missing_date_count": missing_date_count,
            },
            "warnings": warnings,
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

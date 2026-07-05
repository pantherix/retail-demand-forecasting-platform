from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, Integer, String, JSON
from backend.database.models import Base

class ImportTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class ImportTask(Base):
    __tablename__ = "import_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(36), unique=True, nullable=False)  # UUID string
    status = Column(SAEnum(ImportTaskStatus), default=ImportTaskStatus.PENDING, nullable=False)
    progress = Column(Float, default=0.0)  # 0.0 to 100.0
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    result = Column(JSON, nullable=True)  # e.g., {'dataset_id': ..., 'import_batch_id': ...}
    error_message = Column(String(255), nullable=True)

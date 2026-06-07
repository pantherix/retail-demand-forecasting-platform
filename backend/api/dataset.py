from __future__ import annotations

import sys
import io
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.session import get_db
from database.repositories import DatasetRepository, AuditRepository
from auth.dependencies import get_current_user
from database.models import User
from src.data.analyzer import GenericAnalyzer

router = APIRouter(prefix="/dataset", tags=["Dataset Registry"])

DATA_DIR = ROOT / "data" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _quality_score(df: pd.DataFrame) -> float:
    missing    = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()
    penalty    = (missing + duplicates * 2) / max(len(df) * len(df.columns), 1) * 100
    return round(max(100 - penalty, 0), 1)


@router.get("/health")
def health():
    return {"module": "dataset", "status": "healthy"}


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    contents = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
            
        # Best effort date parsing
        for col in df.columns:
            if "date" in col.lower() or "time" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    # Generate insights
    insights = GenericAnalyzer.analyze(df)

    # Save file
    save_path = DATA_DIR / file.filename
    save_path.write_bytes(contents)

    # Queue ML training and inference pipeline
    from forecasting.pipeline import run_pipeline_task
    background_tasks.add_task(run_pipeline_task, save_path, current_user.username)

    sku_count     = df["product_id"].nunique() if "product_id" in df.columns else 0
    quality_score = _quality_score(df)
    
    date_cols = [c for c, v in insights["columns"].items() if v.get("kind") == "datetime"]
    date_from = str(df[date_cols[0]].min().date()) if date_cols else ""
    date_to   = str(df[date_cols[0]].max().date()) if date_cols else ""
    dataset_name = Path(file.filename).stem

    ds = DatasetRepository(db).create(
        name=dataset_name,
        filename=file.filename,
        rows=len(df),
        columns=len(df.columns),
        sku_count=sku_count,
        quality_score=quality_score,
        date_from=date_from,
        date_to=date_to,
        owner=current_user.username,
    )
    AuditRepository(db).log(
        current_user.username, "upload", "dataset",
        f"Uploaded {file.filename} — {len(df)} rows, {len(df.columns)} columns"
    )

    return {
        "success":       True,
        "dataset_id":    ds.id,
        "name":          ds.name,
        "rows":          ds.rows,
        "columns":       ds.columns,
        "quality_score": ds.quality_score,
        "date_range":    f"{date_from} → {date_to}" if date_from else "N/A",
        "owner":         ds.owner,
        "insights":      insights,
    }


@router.get("/list")
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    datasets = DatasetRepository(db).get_all()
    return [
        {
            "id":            d.id,
            "name":          d.name,
            "filename":      d.filename,
            "rows":          d.rows,
            "sku_count":     d.sku_count,
            "quality_score": d.quality_score,
            "date_from":     d.date_from,
            "date_to":       d.date_to,
            "owner":         d.owner,
            "uploaded_at":   str(d.uploaded_at),
        }
        for d in datasets
    ]


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ds = DatasetRepository(db).get_by_id(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

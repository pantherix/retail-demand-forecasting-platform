from __future__ import annotations

import sys
import io
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, BackgroundTasks, Body
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


def sanitize_json_data(obj):
    import math
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: sanitize_json_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_json_data(x) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_json_data(x) for x in obj)
    try:
        import numpy as np
        if isinstance(obj, (np.floating, np.float32, np.float64)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (np.integer, np.int32, np.int64)):
            return int(obj)
    except ImportError:
        pass
    return obj



@router.get("/health")
def health():
    return {"module": "dataset", "status": "healthy"}


def detect_column_mappings(df: pd.DataFrame) -> dict:
    canonical_fields = {
        "sku": {
            "keywords": ["sku", "product_id", "product", "item", "material"],
            "avoid": ["transaction_id", "customer_id", "user_id", "order_id", "supplier_id", "customer", "user", "client", "txn"],
            "exact": "sku"
        },
        "date": {
            "keywords": ["date", "time", "timestamp", "transaction_date"],
            "avoid": [],
            "exact": "date"
        },
        "current_stock": {
            "keywords": ["stock", "inventory", "qty", "quantity", "current_stock", "current stock"],
            "avoid": ["revenue", "price", "cost"],
            "exact": "current_stock"
        },
        "unit_price": {
            "keywords": ["price", "unit_price", "selling_price"],
            "avoid": [],
            "exact": "unit_price"
        },
        "unit_cost": {
            "keywords": ["cost", "unit_cost", "purchase_cost"],
            "avoid": [],
            "exact": "unit_cost"
        },
        "revenue": {
            "keywords": ["revenue", "sales", "amount"],
            "avoid": [],
            "exact": "revenue"
        }
    }

    mappings = {}
    for target, rules in canonical_fields.items():
        candidates = []
        for col in df.columns:
            col_lower = col.lower().strip()
            confidence = 0.1
            
            if col_lower == rules["exact"]:
                confidence = 1.0
            elif col_lower in rules["keywords"]:
                confidence = 0.9
            else:
                for kw in rules["keywords"]:
                    if kw in col_lower:
                        confidence = 0.8
                        break
            
            # Apply avoid/penalty rules
            for av in rules["avoid"]:
                if av in col_lower:
                    confidence = 0.1
                    break
                    
            candidates.append({"column": col, "confidence": round(confidence, 2)})
            
        candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)
        best_match = None
        if candidates and candidates[0]["confidence"] >= 0.5:
            best_match = candidates[0]["column"]
            
        mappings[target] = {
            "best_match": best_match,
            "candidates": candidates
        }
    return mappings


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

    # Save to temp path
    import uuid
    temp_file_id = str(uuid.uuid4())
    safe_filename = Path(file.filename).name
    temp_save_path = (DATA_DIR / f"temp_{temp_file_id}_{safe_filename}").resolve()
    save_path = (DATA_DIR / safe_filename).resolve()

    resolved_data_dir = DATA_DIR.resolve()
    try:
        temp_save_path.relative_to(resolved_data_dir)
        save_path.relative_to(resolved_data_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt detected")

    temp_save_path.write_bytes(contents)
    save_path.write_bytes(contents)

    # Queue ML training and inference pipeline
    from forecasting.pipeline import run_pipeline_task
    background_tasks.add_task(run_pipeline_task, save_path, current_user.username)

    sku_count     = df["product_id"].nunique() if "product_id" in df.columns else (df["sku"].nunique() if "sku" in df.columns else 0)
    quality_score = _quality_score(df)
    
    date_cols = [c for c, v in insights["columns"].items() if v.get("kind") == "datetime"]
    date_from = str(df[date_cols[0]].min().date()) if date_cols else ""
    date_to   = str(df[date_cols[0]].max().date()) if date_cols else ""
    dataset_name = Path(safe_filename).stem

    ds = DatasetRepository(db).create(
        name=dataset_name,
        filename=safe_filename,
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
        "temp_file_id":  temp_file_id,
        "name":          ds.name,
        "rows":          ds.rows,
        "columns":       list(df.columns),
        "columns_count": len(df.columns),
        "sample_data":   sanitize_json_data(df.head(5).to_dict(orient="records")),
        "mappings":      detect_column_mappings(df),
        "quality_score": ds.quality_score,
        "date_range":    f"{date_from} → {date_to}" if date_from else "N/A",
        "owner":         ds.owner,
        "insights":      sanitize_json_data(insights),
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


@router.post("/cleanup")
def cleanup_dataset(
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from database.models import Product, InventoryItem, Sale, Forecast, RiskScore, Alert, Dataset

    # Find valid batch IDs
    valid_batch_ids = [
        d.import_batch_id
        for d in db.query(Dataset).filter(Dataset.import_batch_id != None).all()
    ]

    # Find products to remove
    products_to_remove = (
        db.query(Product)
        .filter(
            (Product.sku == None)
            | (Product.sku == "")
            | (Product.unit_cost < 0)
            | (Product.base_price < 0)
            | (
                (Product.created_by_import == True)
                & ~Product.import_batch_id.in_(valid_batch_ids)
            )
        )
        .all()
    )
    product_ids_to_remove = [p.id for p in products_to_remove]
    product_skus_to_remove = [p.sku for p in products_to_remove if p.sku]

    # Proposed audit survivors proof
    proof_survivors = {}
    for sku in ["10001", "MAT-2001", "ITEM0001"]:
        proof_survivors[sku] = sku not in product_skus_to_remove

    # Proposed deletions audit
    audit_report = {
        "products_to_remove": product_skus_to_remove
    }

    if not confirm:
        return {
            "confirmed": False,
            "audit_report": audit_report,
            "proof_survivors": proof_survivors
        }

    # Otherwise perform cleanup
    all_product_ids = [p.id for p in db.query(Product.id).all()]

    inventory_to_remove = (
        db.query(InventoryItem)
        .filter(
            (InventoryItem.product_id.in_(product_ids_to_remove))
            | (
                (InventoryItem.created_by_import == True)
                & ~InventoryItem.import_batch_id.in_(valid_batch_ids)
            )
            | (~InventoryItem.product_id.in_(all_product_ids))
        )
        .all()
    )
    inventory_ids_to_remove = [x.id for x in inventory_to_remove]

    sales_to_remove = (
        db.query(Sale)
        .filter(
            (Sale.product_id.in_(product_ids_to_remove))
            | (
                (Sale.created_by_import == True)
                & ~Sale.import_batch_id.in_(valid_batch_ids)
            )
            | (~Sale.product_id.in_(all_product_ids))
        )
        .all()
    )
    sales_ids_to_remove = [x.id for x in sales_to_remove]

    forecasts_to_remove = (
        db.query(Forecast)
        .filter(
            (Forecast.product_id.in_(product_ids_to_remove))
            | (
                (Forecast.created_by_import == True)
                & ~Forecast.import_batch_id.in_(valid_batch_ids)
            )
            | (~Forecast.product_id.in_(all_product_ids))
        )
        .all()
    )
    forecasts_ids_to_remove = [x.id for x in forecasts_to_remove]

    risks_to_remove = (
        db.query(RiskScore)
        .filter(
            (RiskScore.product_id.in_(product_ids_to_remove))
            | (
                (RiskScore.created_by_import == True)
                & ~RiskScore.import_batch_id.in_(valid_batch_ids)
            )
            | (~RiskScore.product_id.in_(all_product_ids))
        )
        .all()
    )
    risks_ids_to_remove = [x.id for x in risks_to_remove]

    alerts_to_remove = (
        db.query(Alert)
        .filter(
            (Alert.product_id.in_(product_ids_to_remove))
            | (
                (Alert.created_by_import == True)
                & ~Alert.import_batch_id.in_(valid_batch_ids)
            )
            | (~Alert.product_id.in_(all_product_ids))
        )
        .all()
    )
    alerts_ids_to_remove = [x.id for x in alerts_to_remove]

    products_removed = 0
    inventory_removed = 0
    sales_removed = 0
    forecasts_removed = 0
    risks_removed = 0
    alerts_removed = 0

    if inventory_ids_to_remove:
        inventory_removed = (
            db.query(InventoryItem)
            .filter(InventoryItem.id.in_(inventory_ids_to_remove))
            .delete(synchronize_session=False)
        )
    if sales_ids_to_remove:
        sales_removed = (
            db.query(Sale)
            .filter(Sale.id.in_(sales_ids_to_remove))
            .delete(synchronize_session=False)
        )
    if forecasts_ids_to_remove:
        forecasts_removed = (
            db.query(Forecast)
            .filter(Forecast.id.in_(forecasts_ids_to_remove))
            .delete(synchronize_session=False)
        )
    if risks_ids_to_remove:
        risks_removed = (
            db.query(RiskScore)
            .filter(RiskScore.id.in_(risks_ids_to_remove))
            .delete(synchronize_session=False)
        )
    if alerts_ids_to_remove:
        alerts_removed = (
            db.query(Alert)
            .filter(Alert.id.in_(alerts_ids_to_remove))
            .delete(synchronize_session=False)
        )
    if product_ids_to_remove:
        products_removed = (
            db.query(Product)
            .filter(Product.id.in_(product_ids_to_remove))
            .delete(synchronize_session=False)
        )

    db.commit()

    return {
        "confirmed": True,
        "cleanup_statistics": {
            "products_removed": products_removed,
            "inventory_removed": inventory_removed,
            "sales_removed": sales_removed,
            "forecasts_removed": forecasts_removed,
            "risks_removed": risks_removed,
            "alerts_removed": alerts_removed
        }
    }


@router.post("/import")
def import_dataset(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from database.models import Product, InventoryItem, Sale, Forecast, RiskScore, Alert, Dataset, Warehouse, Supplier
    from datetime import datetime
    import glob
    import re

    temp_file_id = payload.get("temp_file_id")
    source_type = payload.get("source_type", "csv")
    mapping = payload.get("mapping", {})
    confirm_low_confidence = payload.get("confirm_low_confidence", False)

    if not temp_file_id or not isinstance(temp_file_id, str) or not re.match(r"^[a-zA-Z0-9\-]+$", temp_file_id):
        raise HTTPException(status_code=400, detail="Invalid temp_file_id format")

    # Find the temp file
    matching_files = glob.glob(str(DATA_DIR / f"temp_{temp_file_id}_*"))
    if not matching_files:
        raise HTTPException(status_code=404, detail="Temporary file not found")
    
    temp_file_path = Path(matching_files[0]).resolve()
    resolved_data_dir = DATA_DIR.resolve()
    try:
        temp_file_path.relative_to(resolved_data_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path traversal attempt detected")

    original_filename = temp_file_path.name.replace(f"temp_{temp_file_id}_", "")

    # Load file
    try:
        if temp_file_path.name.endswith(".csv") or source_type == "csv":
            df = pd.read_csv(temp_file_path)
        else:
            df = pd.read_excel(temp_file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse temp file: {e}")

    # 1. Required target fields
    if "sku" not in mapping:
        raise HTTPException(status_code=400, detail="Required target field 'sku' is not mapped")
    if "date" not in mapping:
        raise HTTPException(status_code=400, detail="Required target field 'date' is not mapped")

    # 2. Duplicate mapping check
    mapping_vals = [v for v in mapping.values() if v]
    if len(set(mapping_vals)) < len(mapping_vals):
        raise HTTPException(status_code=400, detail="Multiple target fields cannot be mapped to the same source column")

    # 3. Customer identifiers check on SKU
    sku_src = mapping.get("sku")
    if sku_src:
        sku_src_lower = str(sku_src).lower()
        if any(kw in sku_src_lower for kw in ["customer", "user", "client"]):
            raise HTTPException(status_code=400, detail="Mapping customer identifiers to SKU is not allowed.")
        if sku_src not in df.columns:
            raise HTTPException(status_code=400, detail="Invalid source column name for 'sku'")
        sku_keywords = ["sku", "product", "item", "material", "part", "id"]
        if not any(kw in sku_src_lower for kw in sku_keywords):
            raise HTTPException(status_code=400, detail="Invalid source column name for 'sku'")

    # Validate all other mapped columns exist in df
    for canonical, source in mapping.items():
        if source and source not in df.columns:
            raise HTTPException(status_code=400, detail=f"Invalid source column name for '{canonical}'")

    # 4. Check confidence score validation rejection
    detected = detect_column_mappings(df)
    for canonical, source in mapping.items():
        if source:
            candidates = detected.get(canonical, {}).get("candidates", [])
            confidence = 0.0
            for cand in candidates:
                if cand["column"] == source:
                    confidence = cand["confidence"]
                    break
            if confidence < 0.5 and not confirm_low_confidence:
                raise HTTPException(status_code=400, detail=f"Low confidence mapping detected for '{canonical}'. Please confirm to proceed.")

    # 5. Quality score and import rows
    # Compute quality score penalty
    penalty = 0.0
    valid_rows = []
    
    # Standardize types
    date_col = mapping.get("date")
    sku_col = mapping.get("sku")
    qty_col = mapping.get("current_stock")
    price_col = mapping.get("unit_price")
    cost_col = mapping.get("unit_cost")
    rev_col = mapping.get("revenue")

    for idx, row in df.iterrows():
        sku_val = str(row[sku_col]).strip() if sku_col and not pd.isna(row[sku_col]) else ""
        if not sku_val or sku_val == "":
            # Skipped early
            continue
            
        valid_rows.append(row)
        
        # Penalties for negative values
        if qty_col and not pd.isna(row[qty_col]) and float(row[qty_col]) < 0:
            penalty += 4.0
        if rev_col and not pd.isna(row[rev_col]) and float(row[rev_col]) < 0:
            penalty += 4.0
        if price_col and not pd.isna(row[price_col]) and float(row[price_col]) < 0:
            penalty += 4.0
        if cost_col and not pd.isna(row[cost_col]) and float(row[cost_col]) < 0:
            penalty += 4.0

    quality_score = max(100.0 - penalty, 0.0)

    # 6. Database ingestion
    batch_id = temp_file_id  # Use the temp_file_id as the import_batch_id!
    
    # Create dataset entry
    parsed_dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
    date_from_val = str(parsed_dates.min().date()) if not parsed_dates.empty else ""
    date_to_val = str(parsed_dates.max().date()) if not parsed_dates.empty else ""

    ds = Dataset(
        name=Path(original_filename).stem,
        filename=original_filename,
        rows=len(df),
        columns=len(df.columns),
        sku_count=df[sku_col].nunique() if sku_col else 0,
        quality_score=quality_score,
        date_from=date_from_val,
        date_to=date_to_val,
        owner=current_user.username,
        import_batch_id=batch_id,
        uploaded_at=datetime.utcnow()
    )
    db.add(ds)
    db.flush()

    # Get active dependencies or create placeholders
    wh = db.query(Warehouse).first()
    if not wh:
        wh = Warehouse(name="Warehouse A", location="North Regional Hub (Delhi)", capacity=15000.0, utilization=42.5)
        db.add(wh)
        db.flush()
        
    sup = db.query(Supplier).first()
    if not sup:
        sup = Supplier(name="Apex Wholesale", lead_time_days=5, reliability_score=98.8, fill_rate=99.1)
        db.add(sup)
        db.flush()

    for row in valid_rows:
        sku_val = str(row[sku_col]).strip()
        
        prod = db.query(Product).filter(Product.sku == sku_val).first()
        if not prod:
            avg_price = float(row[price_col]) if price_col and not pd.isna(row[price_col]) else 100.0
            avg_cost = float(row[cost_col]) if cost_col and not pd.isna(row[cost_col]) else 40.0
            prod = Product(
                sku=sku_val,
                name=f"Organic {sku_val} Item",
                category="General",
                subcategory="Longtail",
                base_price=avg_price,
                unit_cost=avg_cost,
                lead_time_days=sup.lead_time_days,
                safety_stock=20.0,
                reorder_point=60.0,
                abc_class="C",
                supplier_id=sup.id,
                created_by_import=True,
                import_batch_id=batch_id,
                import_timestamp=datetime.utcnow()
            )
            db.add(prod)
            db.flush()

        # Update InventoryItem
        current_stock_val = float(row[qty_col]) if qty_col and not pd.isna(row[qty_col]) else 10.0
        inv = db.query(InventoryItem).filter(InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == wh.id).first()
        if inv:
            inv.current_stock = current_stock_val
            inv.import_batch_id = batch_id
            inv.created_by_import = True
            inv.import_timestamp = datetime.utcnow()
        else:
            inv = InventoryItem(
                product_id=prod.id,
                warehouse_id=wh.id,
                current_stock=current_stock_val,
                created_by_import=True,
                import_batch_id=batch_id,
                import_timestamp=datetime.utcnow()
            )
            db.add(inv)

        # Create Sale record
        sale_date_val = pd.to_datetime(row[date_col]).to_pydatetime() if date_col and not pd.isna(row[date_col]) else datetime.utcnow()
        sale = Sale(
            product_id=prod.id,
            warehouse_id=wh.id,
            quantity=float(row[qty_col]) if qty_col and not pd.isna(row[qty_col]) else 1.0,
            price=prod.base_price,
            cost=prod.unit_cost,
            transaction_date=sale_date_val,
            created_by_import=True,
            import_batch_id=batch_id,
            import_timestamp=datetime.utcnow()
        )
        db.add(sale)

    db.commit()

    return {
        "success": True,
        "dataset_id": ds.id,
        "quality_score": quality_score,
        "metrics": {
            "imported_rows": len(valid_rows),
            "rejected_rows": 0
        }
    }



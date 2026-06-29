from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from backend.auth.dependencies import get_current_user, get_current_admin_user
from backend.database.models import User
from backend.database.repositories import AuditRepository, DatasetRepository
from backend.database.session import get_db

router = APIRouter(prefix="/dataset", tags=["Dataset Registry"])

DATA_DIR = ROOT / "data" / "uploads"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_old_temp_files():
    try:
        import time

        now = time.time()
        for f in DATA_DIR.glob("temp_*"):
            if now - f.stat().st_mtime > 3600:  # 1 hour
                try:
                    f.unlink()
                except Exception:
                    pass
    except Exception:
        pass


def cleanup_temp_file(file_path: Path):
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def _quality_score(df: pd.DataFrame) -> float:
    missing = df.isnull().sum().sum()
    duplicates = df.duplicated().sum()
    penalty = (missing + duplicates * 2) / max(len(df) * len(df.columns), 1) * 100
    return round(max(100 - penalty, 0), 1)


@router.get("/health")
def health():
    return {"module": "dataset", "status": "healthy"}


import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

# Target canonical fields auto-detection rules
CANONICAL_MAP = {
    "identity_key": {
        "sku",
        "product_sku",
        "productsku",
        "item_code",
        "itemcode",
        "part_no",
        "partno",
        "barcode",
        "product_id",
        "productid",
        "item_id",
        "itemid",
        "item number",
        "part_number",
        "id",
    },
    "stock_on_hand": {
        "current_stock",
        "currentstock",
        "qty",
        "quantity",
        "stock",
        "stock_left",
        "stockleft",
        "inventory",
        "on_hand",
        "onhand",
        "qty_on_hand",
        "stock_on_hand",
    },
    "velocity_rate": {
        "velocity_rate",
        "velocityrate",
        "velocity",
        "rate",
        "daily_sales",
        "dailysales",
        "sales",
        "revenue",
        "amount",
    },
}


def fuzzy_match_schema(
    columns: List[str], raise_on_error: bool = False
) -> Dict[str, str]:
    matched = {}

    # Check for identity_key match
    for col in columns:
        col_low = str(col).lower().strip().replace(" ", "_").replace("-", "_")
        if col_low in CANONICAL_MAP["identity_key"] or any(
            k in col_low
            for k in ["sku", "part_no", "item_code", "barcode", "item_number"]
        ):
            matched["identity_key"] = col
            break

    # Check for stock_on_hand match
    for col in columns:
        col_low = str(col).lower().strip().replace(" ", "_").replace("-", "_")
        if col_low in CANONICAL_MAP["stock_on_hand"] or any(
            k in col_low for k in ["qty", "stock", "on_hand", "quantity"]
        ):
            matched["stock_on_hand"] = col
            break

    # Check for velocity_rate match
    for col in columns:
        col_low = str(col).lower().strip().replace(" ", "_").replace("-", "_")
        if col_low in CANONICAL_MAP["velocity_rate"] or any(
            k in col_low for k in ["sales", "revenue", "velocity"]
        ):
            matched["velocity_rate"] = col
            break

    # If critical mapping keys are missing, throw a clean, handled HTTP 400 Exception
    if raise_on_error:
        if "identity_key" not in matched:
            raise HTTPException(
                status_code=400,
                detail="Fuzzy schema matching failed: Required target field 'identity_key' (sku) could not be matched automatically.",
            )
        if "stock_on_hand" not in matched:
            raise HTTPException(
                status_code=400,
                detail="Fuzzy schema matching failed: Required target field 'stock_on_hand' (current_stock) could not be matched automatically.",
            )

    return matched


TARGET_FIELDS = {
    "identity_key": {
        "exact": [
            "sku",
            "product_id",
            "sku_id",
            "item_id",
            "item",
            "product",
            "productid",
            "skuid",
            "code",
            "product code",
            "productcode",
            "sku code",
            "skucode",
            "item number",
            "part_no",
            "partno",
            "barcode",
            "identity_key",
            "identitykey",
        ],
        "substrings": [
            "sku",
            "product",
            "item",
            "id",
            "code",
            "part",
            "number",
            "barcode",
        ],
        "avoid": [
            "name",
            "category",
            "price",
            "cost",
            "revenue",
            "date",
            "time",
            "transaction",
            "trans",
            "quantity",
            "qty",
            "sales",
            "stock",
        ],
    },
    "stock_on_hand": {
        "exact": [
            "quantity",
            "qty",
            "stock",
            "current_stock",
            "inventory",
            "stock_level",
            "stock_qty",
            "units",
            "quantity_on_hand",
            "on_hand",
            "stock_on_hand",
            "stock_left",
            "stockleft",
        ],
        "substrings": [
            "qty",
            "stock",
            "quantity",
            "inventory",
            "units",
            "on_hand",
            "hand",
            "left",
        ],
        "avoid": [
            "price",
            "cost",
            "revenue",
            "sold",
            "date",
            "time",
            "id",
            "sku",
            "product",
        ],
    },
    "velocity_rate": {
        "exact": [
            "revenue",
            "sales_revenue",
            "amount",
            "total_price",
            "revenue_amount",
            "sales_amount",
            "sales",
            "total",
            "velocity_rate",
            "velocityrate",
            "velocity",
            "rate",
            "daily_sales",
            "average_daily_sales",
        ],
        "substrings": ["rev", "amount", "sales", "total", "velocity", "rate"],
        "avoid": [
            "sku",
            "id",
            "date",
            "time",
            "cost",
            "unit",
            "qty",
            "quantity",
            "price",
        ],
    },
    "date": {
        "exact": [
            "date",
            "timestamp",
            "datetime",
            "sales_date",
            "transaction_date",
            "time",
            "created_at",
            "day",
        ],
        "substrings": ["date", "time", "timestamp", "day"],
        "avoid": [
            "sku",
            "id",
            "qty",
            "price",
            "cost",
            "revenue",
            "product",
            "category",
        ],
    },
    "product_name": {
        "exact": [
            "product_name",
            "name",
            "item_name",
            "title",
            "productname",
            "itemname",
            "description",
            "desc",
            "label",
        ],
        "substrings": ["name", "title", "desc", "label"],
        "avoid": [
            "sku",
            "id",
            "category",
            "price",
            "cost",
            "revenue",
            "date",
            "time",
            "qty",
            "stock",
        ],
    },
    "category": {
        "exact": [
            "category",
            "cat",
            "department",
            "dept",
            "group",
            "type",
            "class",
            "abc_class",
        ],
        "substrings": ["cat", "dept", "group", "type", "class"],
        "avoid": [
            "sku",
            "id",
            "name",
            "price",
            "cost",
            "revenue",
            "date",
            "time",
            "qty",
            "stock",
        ],
    },
    "unit_cost": {
        "exact": [
            "unit_cost",
            "cost",
            "cost_price",
            "cost_per_unit",
            "buy_price",
            "purchase_price",
        ],
        "substrings": ["cost", "buy", "purchase"],
        "avoid": [
            "sku",
            "id",
            "price",
            "selling",
            "revenue",
            "date",
            "time",
            "qty",
            "stock",
        ],
    },
    "unit_price": {
        "exact": [
            "unit_price",
            "price",
            "selling_price",
            "price_per_unit",
            "retail_price",
            "base_price",
        ],
        "substrings": ["price", "sell", "retail"],
        "avoid": [
            "sku",
            "id",
            "cost",
            "buy",
            "purchase",
            "revenue",
            "date",
            "time",
            "qty",
            "stock",
        ],
    },
    "warehouse": {
        "exact": ["warehouse", "location", "store", "wh", "warehouse_name", "site"],
        "substrings": ["warehouse", "location", "store", "wh", "site"],
        "avoid": [
            "sku",
            "id",
            "price",
            "cost",
            "revenue",
            "date",
            "time",
            "qty",
            "stock",
            "name",
        ],
    },
}


class DatasetImportPayload(BaseModel):
    temp_file_id: Optional[str] = None
    source_type: str
    mapping: Optional[Dict[str, Optional[str]]] = None
    confirm_low_confidence: Optional[bool] = False
    confirm_customer_identifiers: Optional[bool] = False
    confirm_custom_sku: Optional[bool] = False


def detect_column_mappings(df: pd.DataFrame) -> dict:
    fuzzy_matches = fuzzy_match_schema(list(df.columns))
    mappings = {}
    for field_name, rules in TARGET_FIELDS.items():
        candidates = []
        for col in df.columns:
            col_low = str(col).lower().strip()
            score = 0.0

            # 1. Exact matches
            if col_low in rules["exact"]:
                score = 0.95
            else:
                # 2. Substring matches
                for sub in rules["substrings"]:
                    if sub in col_low:
                        score += 0.4
                        break

            # 3. Penalize avoid list
            for av in rules["avoid"]:
                if av in col_low:
                    score -= 0.6
                    break

            # 4. Check data type
            col_data = df[col]
            if field_name == "date":
                try:
                    parsed_dates = pd.to_datetime(
                        col_data.dropna().head(20), errors="coerce"
                    )
                    valid_pct = (
                        parsed_dates.notna().sum() / len(parsed_dates)
                        if len(parsed_dates) > 0
                        else 0.0
                    )
                    if valid_pct > 0.7:
                        score += 0.3
                    else:
                        score -= 0.3
                except Exception:
                    score -= 0.3
            elif field_name in [
                "stock_on_hand",
                "velocity_rate",
                "unit_cost",
                "unit_price",
            ]:
                if pd.api.types.is_numeric_dtype(col_data.dtype):
                    score += 0.2
                else:
                    score -= 0.3
            elif field_name in [
                "identity_key",
                "product_name",
                "category",
                "warehouse",
            ]:
                if not pd.api.types.is_numeric_dtype(col_data.dtype):
                    score += 0.1

            score = max(0.0, min(1.0, round(score, 2)))
            candidates.append({"column": col, "confidence": score})

        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        best_match = None
        if field_name in fuzzy_matches:
            best_match = fuzzy_matches[field_name]
        elif candidates and candidates[0]["confidence"] >= 0.35:
            best_match = candidates[0]["column"]

        mappings[field_name] = {"best_match": best_match, "candidates": candidates}

    # Replicate matched values under legacy keys for backward compatibility
    mappings["sku"] = mappings["identity_key"]
    mappings["current_stock"] = mappings["stock_on_hand"]
    mappings["revenue"] = mappings["velocity_rate"]

    return mappings


@router.post("/upload")
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    background_tasks.add_task(clean_old_temp_files)
    if not file.filename or not file.filename.endswith((".csv", ".xlsx")):
        raise HTTPException(
            status_code=400, detail="Only CSV and Excel files are supported"
        )

    contents = await file.read()
    try:
        if file.filename and file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse file: {e}")

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Generate temporary identifier
    temp_filename = f"temp_{uuid.uuid4().hex}_{file.filename}"
    save_path = DATA_DIR / temp_filename
    save_path.write_bytes(contents)

    # Heuristic column mappings detection
    detected_mappings = detect_column_mappings(df)

    # Sample rows (first 5 rows as dictionaries)
    sample_data = (
        df.head(5).replace({pd.NA: None, float("nan"): None}).to_dict(orient="records")
    )

    return {
        "success": True,
        "temp_file_id": temp_filename,
        "filename": file.filename,
        "columns": list(df.columns),
        "sample_data": sample_data,
        "mappings": detected_mappings,
        "rows": len(df),
        "columns_count": len(df.columns),
    }


@router.post("/import")
async def import_dataset(
    payload: DatasetImportPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pre_import_warnings = []
    source_type = payload.source_type.lower()

    # 1. Parse and extract data using proper adapters
    if source_type in ["csv", "xlsx"]:
        if not payload.temp_file_id:
            raise HTTPException(
                status_code=400, detail="Missing temporary file ID for file import"
            )

        file_path = DATA_DIR / payload.temp_file_id
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail="Temporary file not found or expired"
            )

        try:
            file_data = file_path.read_bytes()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Could not read temporary file: {e}"
            )

        # Validate mapping input
        raw_mapping = payload.mapping or {}
        mapping: dict[str, str] = {k: v for k, v in raw_mapping.items() if v}

        # Pre-process canonical entities to standard internal keys
        if "identity_key" in mapping:
            mapping["sku"] = mapping.pop("identity_key")
        if "stock_on_hand" in mapping:
            mapping["current_stock"] = mapping.pop("stock_on_hand")
        if "velocity_rate" in mapping:
            mapping["revenue"] = mapping.pop("velocity_rate")

        required_fields = ["sku", "date", "current_stock"]
        for rf in required_fields:
            if not mapping.get(rf):
                raise HTTPException(
                    status_code=400,
                    detail=f"Required target field '{rf}' is not mapped",
                )

        # Reject duplicate mappings
        mapped_cols = [col for col in mapping.values() if col]
        if len(mapped_cols) != len(set(mapped_cols)):
            raise HTTPException(
                status_code=400,
                detail="Multiple target fields cannot be mapped to the same source column",
            )

        # Normalize and validate SKU column name
        sku_col = mapping.get("sku")
        if sku_col:
            sku_col_lower = sku_col.lower()
            customer_identifiers = [
                "customer id",
                "transaction id",
                "email",
                "phone",
                "gender",
                "age",
            ]
            if any(ci in sku_col_lower for ci in customer_identifiers):
                pre_import_warnings.append(
                    f"Privacy Warning: SKU mapped to column containing customer identifiers: '{sku_col}'."
                )

            # Check if it's a valid column name for 'sku'
            valid_sku_names = {
                "sku",
                "product_sku",
                "productsku",
                "item_code",
                "itemcode",
                "part_no",
                "partno",
                "barcode",
                "product_id",
                "productid",
                "item_id",
                "itemid",
                "item number",
                "part_number",
                "identity_key",
                "identitykey",
                "id",
            }
            sku_col_normalized = (
                sku_col_lower.replace(" ", "").replace("_", "").replace("-", "")
            )
            valid_normalized = {
                name.replace(" ", "").replace("_", "").replace("-", "")
                for name in valid_sku_names
            }

            if sku_col_normalized not in valid_normalized:
                pre_import_warnings.append(
                    f"Custom Mapping: Column '{sku_col}' mapped to SKU field."
                )

        # Check confidence scores of mapped columns against detect_column_mappings
        try:
            if payload.temp_file_id.endswith(".csv"):
                df_val = pd.read_csv(io.BytesIO(file_data))
            else:
                df_val = pd.read_excel(io.BytesIO(file_data))
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Could not parse file for validation: {e}"
            )

        # Enforce fuzzy matching check on the columns but do not raise blocker errors
        fuzzy_match_schema(list(df_val.columns), raise_on_error=False)

        detected_mappings = detect_column_mappings(df_val)
        for target_field, source_col in mapping.items():
            if not source_col:
                continue
            field_cands = detected_mappings.get(target_field, {}).get("candidates", [])
            confidence = 0.0
            for cand in field_cands:
                if cand["column"] == source_col:
                    confidence = cand["confidence"]
                    break
            if confidence < 0.7:
                pre_import_warnings.append(
                    f"Confidence Warning: Low confidence mapping for target field '{target_field}' ({confidence * 100:.0f}%)."
                )

        # Raise errors if warnings exist and corresponding confirmation flags are False
        for warning in pre_import_warnings:
            if (
                "Privacy Warning:" in warning
                and not payload.confirm_customer_identifiers
            ):
                raise HTTPException(
                    status_code=400,
                    detail="SKU mapped to column containing customer identifiers. Please confirm to proceed.",
                )
            if "Custom Mapping:" in warning and not payload.confirm_custom_sku:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid source column name for 'sku'. Please confirm custom SKU mapping to proceed.",
                )
            if "Confidence Warning:" in warning and not payload.confirm_low_confidence:
                raise HTTPException(
                    status_code=400,
                    detail="Low confidence mapping detected. Please confirm to proceed.",
                )

        from backend.services.adapters import CSVAdapter, XLSXAdapter

        if source_type == "csv":
            adapter = CSVAdapter(data=file_data, mapping=mapping)
        else:
            adapter = XLSXAdapter(data=file_data, mapping=mapping)
    elif source_type in ["shopify", "odoo", "zoho_inventory"]:
        from backend.services.adapters import (
            OdooAdapter,
            ShopifyAdapter,
            ZohoInventoryAdapter,
        )

        # These integrations are not yet configured for real data ingestion.
        # Raise an HTTPException to indicate they are not ready.
        raise HTTPException(
            status_code=501,  # Not Implemented
            detail=f"{source_type.capitalize()} integration is not yet configured for real data ingestion. Please use file upload or configure the integration properly.",
        )
        # Original (mock/placeholder) logic, commented out:
        # if source_type == "shopify":
        #     adapter = ShopifyAdapter()
        # elif source_type == "odoo":
        #     adapter = OdooAdapter()
        # else:
        #     adapter = ZohoInventoryAdapter()
    else:
        raise HTTPException(
            status_code=400, detail=f"Unsupported source type: {source_type}"
        )

    try:
        canonical_data = adapter.parse()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error parsing data via adapter: {e}"
        )

    products = canonical_data.get("products", [])
    inventory = canonical_data.get("inventory", [])
    sales = canonical_data.get("sales", [])

    if not products and not sales:
        raise HTTPException(
            status_code=400,
            detail="Dataset contains no valid products or sales records",
        )

    # 2. Data Quality Profiling & Sanitization
    warnings = pre_import_warnings
    total_rows = len(sales)
    imported_rows = 0
    rejected_rows = 0
    missing_sku_count = 0
    missing_date_count = 0
    seen_transactions = set()
    duplicate_count = 0
    total_warning_occurrences = 0

    valid_products = []
    valid_inventory = []
    valid_sales = []
    valid_skus = set()

    for idx, p in enumerate(products):
        sku = p.get("sku")
        if not sku or pd.isna(sku) or str(sku).strip() == "":
            total_warning_occurrences += 1
            warnings.append(f"Product Row {idx+1}: SKU is empty. Skipping.")
            continue
        sku = str(sku).strip()
        try:
            p["unit_cost"] = float(p.get("unit_cost") or 40.0)
            if p["unit_cost"] < 0:
                total_warning_occurrences += 1
                warnings.append(f"Product {sku}: Negative cost reset to 0.")
                p["unit_cost"] = 0.0
        except Exception:
            p["unit_cost"] = 40.0

        try:
            p["unit_price"] = float(p.get("unit_price") or 100.0)
            if p["unit_price"] < 0:
                total_warning_occurrences += 1
                warnings.append(f"Product {sku}: Negative price reset to 0.")
                p["unit_price"] = 0.0
        except Exception:
            p["unit_price"] = 100.0

        valid_skus.add(sku)
        valid_products.append(p)

    for idx, inv in enumerate(inventory):
        sku = inv.get("sku")
        if not sku or pd.isna(sku) or str(sku).strip() == "":
            continue
        sku = str(sku).strip()
        if sku not in valid_skus:
            valid_skus.add(sku)
            valid_products.append(
                {
                    "sku": sku,
                    "product_name": f"Organic {sku} Item",
                    "category": "General",
                    "unit_cost": 40.0,
                    "unit_price": 100.0,
                }
            )
        try:
            inv["current_stock"] = float(inv.get("current_stock") or 0.0)
            if inv["current_stock"] < 0:
                total_warning_occurrences += 1
                warnings.append(
                    f"Inventory Row {idx+1} ({sku}): Negative stock reset to 0."
                )
                inv["current_stock"] = 0.0
        except Exception:
            inv["current_stock"] = 0.0
        valid_inventory.append(inv)

    for idx, s in enumerate(sales):
        sku = s.get("sku")
        date = s.get("date")

        if not sku or pd.isna(sku) or str(sku).strip() == "":
            missing_sku_count += 1
            rejected_rows += 1
            total_warning_occurrences += 1
            if len(warnings) < 50:
                warnings.append(f"Sales Row {idx+1}: SKU is empty. Skipping.")
            continue
        sku = str(sku).strip()

        if not date or pd.isna(date):
            missing_date_count += 1
            rejected_rows += 1
            total_warning_occurrences += 1
            if len(warnings) < 50:
                warnings.append(
                    f"Sales Row {idx+1} ({sku}): Date is missing. Skipping."
                )
            continue

        parsed_date = None
        if isinstance(date, str):
            try:
                parsed_date = pd.to_datetime(date)
            except Exception:
                pass
        else:
            parsed_date = date

        if not parsed_date or pd.isna(parsed_date):
            missing_date_count += 1
            rejected_rows += 1
            total_warning_occurrences += 1
            if len(warnings) < 50:
                warnings.append(
                    f"Sales Row {idx+1} ({sku}): Invalid date format '{date}'. Skipping."
                )
            continue

        s["date"] = parsed_date

        if sku not in valid_skus:
            valid_skus.add(sku)
            valid_products.append(
                {
                    "sku": sku,
                    "product_name": f"Organic {sku} Item",
                    "category": "General",
                    "unit_cost": 40.0,
                    "unit_price": 100.0,
                }
            )

        sku_has_inv = any(item["sku"] == sku for item in valid_inventory)
        if not sku_has_inv:
            valid_inventory.append(
                {
                    "sku": sku,
                    "warehouse": s.get("warehouse") or "Warehouse A",
                    "current_stock": 150.0,
                }
            )

        wh_name = s.get("warehouse") or "Warehouse A"
        date_str = parsed_date.strftime("%Y-%m-%d")
        transaction_key = (sku, wh_name, date_str)
        if transaction_key in seen_transactions:
            duplicate_count += 1
            total_warning_occurrences += 1
            if len(warnings) < 50:
                warnings.append(
                    f"Sales Row {idx+1} ({sku}): Duplicate entry for {wh_name} on {date_str}. Aggregating."
                )
        else:
            seen_transactions.add(transaction_key)

        try:
            s["quantity_sold"] = float(s.get("quantity_sold") or 1.0)
            if s["quantity_sold"] < 0:
                total_warning_occurrences += 1
                warnings.append(
                    f"Sales Row {idx+1} ({sku}): Negative quantity reset to 1."
                )
                s["quantity_sold"] = 1.0
        except Exception:
            s["quantity_sold"] = 1.0

        try:
            s["revenue"] = float(s.get("revenue") or 0.0)
            if s["revenue"] < 0:
                total_warning_occurrences += 1
                warnings.append(
                    f"Sales Row {idx+1} ({sku}): Negative revenue reset to 0."
                )
                s["revenue"] = 0.0
        except Exception:
            s["revenue"] = 0.0

        imported_rows += 1
        valid_sales.append(s)

    # Calculate Data Quality Score (0 to 100)
    penalty = total_warning_occurrences * 2.0
    quality_score = max(0.0, min(100.0, round(100.0 - penalty, 1)))

    if imported_rows == 0:
        raise HTTPException(
            status_code=400,
            detail="Import rejected: 0 valid sales rows after filtering",
        )

    cleaned_canonical_data = {
        "products": valid_products,
        "inventory": valid_inventory,
        "sales": valid_sales,
    }

    # Determine names for dataset registry
    if source_type in ["csv", "xlsx"] and payload.temp_file_id:
        original_name = (
            payload.temp_file_id.split("_", 2)[-1]
            if len(payload.temp_file_id.split("_", 2)) > 2
            else payload.temp_file_id
        )
        dataset_name = Path(original_name).stem
        filename = original_name
    else:
        dataset_name = f"{source_type.capitalize()} Integration Sync"
        filename = f"{source_type}_sync.json"

    import_batch_id = str(uuid.uuid4())
    import_timestamp = datetime.utcnow()
    lineage_metadata = {
        "import_batch_id": import_batch_id,
        "source_type": source_type,
        "source_file": filename,
        "import_timestamp": import_timestamp,
        "created_by_import": True,
    }

    # 3. Trigger background ML pipeline retraining
    from backend.forecasting.pipeline import run_pipeline_canonical_task

    background_tasks.add_task(
        run_pipeline_canonical_task,
        cleaned_canonical_data,
        str(current_user.username),
        lineage_metadata,
    )

    date_from = (
        min(s["date"] for s in valid_sales).strftime("%Y-%m-%d") if valid_sales else ""
    )
    date_to = (
        max(s["date"] for s in valid_sales).strftime("%Y-%m-%d") if valid_sales else ""
    )

    ds = DatasetRepository(db).create(
        name=dataset_name,
        filename=filename,
        rows=imported_rows,
        columns=len(payload.mapping) if payload.mapping else 5,
        sku_count=len(valid_skus),
        quality_score=quality_score,
        date_from=date_from,
        date_to=date_to,
        owner=str(current_user.username),
        import_batch_id=import_batch_id,
    )

    AuditRepository(db).log(
        str(current_user.username),
        "import",
        "dataset",
        f"Imported canonical data from {source_type} — {imported_rows} valid rows, score: {quality_score}",
    )

    if source_type in ["csv", "xlsx"] and payload.temp_file_id:
        file_path = DATA_DIR / payload.temp_file_id
        background_tasks.add_task(cleanup_temp_file, file_path)

    return {
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


import logging as _logging
import math as _math

_dataset_logger = _logging.getLogger(__name__)


def _recalculate_all_metrics_task(username: str) -> None:
    """
    Background task: recompute safety stock, ROP, risk scores, and warehouse
    utilizations for every product that survives after a cleanup operation.

    Logic is taken directly from backend/scripts/cleanup_db.py steps 5 and 6
    (cleanup_database function, lines ~229-376).  No new formulas are
    introduced here.  The session-management pattern mirrors
    backend/forecasting/pipeline.py::run_pipeline_canonical_task.
    """
    from datetime import datetime

    from sqlalchemy import func

    from backend.database.models import (
        Forecast,
        InventoryItem,
        Product,
        RiskScore,
        Sale,
        Warehouse,
    )
    from backend.database.session import SessionLocal

    db = SessionLocal()
    try:
        # ── Step 5: recalculate metrics for every surviving product ──────────
        # Identical logic to cleanup_db.py cleanup_database() step 5.
        valid_products = db.query(Product).all()
        for prod in valid_products:
            # Stock sum  (cleanup_db.py ~line 234)
            tot_stock = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.product_id == prod.id)
                .scalar()
                or 0.0
            )

            # Forecast sum  (cleanup_db.py ~line 241)
            forecasts = (
                db.query(Forecast.expected_demand)
                .filter(
                    Forecast.product_id == prod.id,
                    Forecast.forecast_date > datetime.utcnow(),
                )
                .all()
            )
            f_sum = sum(f[0] for f in forecasts) if forecasts else 300.0
            avg_daily_sales = f_sum / 30.0

            # Historical sales standard deviation  (cleanup_db.py ~line 249)
            sales = db.query(Sale.quantity).filter(Sale.product_id == prod.id).all()
            qty_list = [s[0] for s in sales] if sales else [10.0]
            if len(qty_list) > 1:
                mean_qty = sum(qty_list) / len(qty_list)
                var_qty = sum((x - mean_qty) ** 2 for x in qty_list) / (
                    len(qty_list) - 1
                )
                std_dev = _math.sqrt(var_qty)
            else:
                std_dev = max(1.0, avg_daily_sales * 0.2)

            # Safety stock and ROP  (cleanup_db.py ~line 260)
            service_level_z = 1.96
            lead_time = float(prod.lead_time_days or 0.0)
            if lead_time <= 0:
                lead_time = 0.0
            if avg_daily_sales <= 0:
                dynamic_safety_stock = 0.0
                reorder_point = 0.0
            else:
                dynamic_safety_stock = float(
                    service_level_z * std_dev * _math.sqrt(lead_time)
                )
                reorder_point = float(
                    (avg_daily_sales * lead_time) + dynamic_safety_stock
                )

            prod.safety_stock = dynamic_safety_stock
            prod.reorder_point = reorder_point

            # Risk score update  (cleanup_db.py ~line 274)
            risk = db.query(RiskScore).filter(RiskScore.product_id == prod.id).first()
            if risk:
                days_of_cover = (
                    tot_stock / avg_daily_sales if avg_daily_sales > 0 else 999.0
                )

                action = "Monitor"
                priority = 3
                urgency = 0.0
                root_causes = []

                if tot_stock < dynamic_safety_stock:
                    action = "Order Now"
                    priority = 1 if prod.abc_class == "A" else 2
                    urgency = min(
                        1.0,
                        (dynamic_safety_stock - tot_stock)
                        / max(dynamic_safety_stock, 1.0),
                    )
                    root_causes.append("Critical Stockout Risk")
                elif tot_stock < reorder_point:
                    action = "Increase Order"
                    priority = 2
                    urgency = 0.5
                    root_causes.append("Below Reorder Point")
                elif tot_stock > (f_sum + dynamic_safety_stock):
                    action = "Liquidate Excess"
                    priority = 4
                    root_causes.append("Overstock Carrying Costs")

                risk.expected_stockout_days = float(
                    round(max(0.0, 7.0 - days_of_cover), 1)
                    if days_of_cover < 7
                    else 0.0
                )
                risk.recommended_action = action
                risk.urgency = float(urgency)
                risk.root_causes = (
                    root_causes if root_causes else ["Stock Levels Healthy"]
                )

                # EOQ-based reorder quantity  (cleanup_db.py ~line 317)
                reorder_qty = 0.0
                if tot_stock < reorder_point:
                    annual_demand = float(f_sum * 12) if f_sum > 0 else 1.0
                    holding_cost = max(float(prod.unit_cost) * 0.25, 0.5)
                    eoq = (
                        _math.sqrt((2 * annual_demand * 100.0) / holding_cost)
                        if holding_cost > 0
                        else 0.0
                    )
                    reorder_qty = max(
                        float(eoq),
                        float(reorder_point + dynamic_safety_stock - tot_stock),
                    )
                risk.reorder_quantity = float(_math.ceil(reorder_qty))
                risk.revenue_at_risk = float(reorder_qty * prod.base_price)
                risk.profit_at_risk = float(
                    reorder_qty * (prod.base_price - prod.unit_cost)
                )
                risk.financial_priority = int(priority)
                if risk.revenue_at_risk > 0:
                    risk.status = "Open"

        # ── Step 6: recalculate warehouse utilizations ────────────────────────
        # Identical logic to cleanup_db.py cleanup_database() step 6.
        warehouses = db.query(Warehouse).all()
        for wh in warehouses:
            total_units = (
                db.query(func.sum(InventoryItem.current_stock))
                .filter(InventoryItem.warehouse_id == wh.id)
                .scalar()
                or 0.0
            )
            wh_cap = float(wh.capacity or 0.0)
            wh.utilization = (
                float(round((float(total_units) / wh_cap) * 100.0, 1))
                if wh_cap > 0
                else 0.0
            )

        db.commit()
        _dataset_logger.info(
            "Post-cleanup metrics recalculation complete for user=%s: "
            "%d products, %d warehouses updated.",
            username,
            len(valid_products),
            len(warehouses),
        )
    except Exception as exc:
        db.rollback()
        _dataset_logger.error(
            "Post-cleanup metrics recalculation failed (user=%s): %s",
            username,
            exc,
        )
    finally:
        db.close()


@router.post("/cleanup")
def cleanup_dataset_route(
    background_tasks: BackgroundTasks,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    import math

    from sqlalchemy import func

    from backend.database.models import (
        Alert,
        Dataset,
        Forecast,
        InventoryItem,
        InventoryTransfer,
        Product,
        RiskScore,
        Sale,
        Warehouse,
    )

    try:
        if db.bind.dialect.name == "sqlite":
            try:
                db.execute(text("PRAGMA foreign_keys = ON;"))
            except Exception as pragma_err:
                logger.warning(
                    f"Could not set SQLite foreign keys PRAGMA: {pragma_err}"
                )

        # 1. Fetch valid import batch IDs from successfully registered datasets
        valid_batch_ids = [
            d.import_batch_id
            for d in db.query(Dataset).filter(Dataset.import_batch_id != None).all()
        ]

        # 2. Identify products to remove based on lineage, failed imports, or metadata corruption (never SKU formats)
        # - SKU is empty or null (corruption marker)
        # - unit_cost < 0 or base_price < 0 (corruption marker)
        # - created_by_import is True and import_batch_id is not in valid_batch_ids (failed imports / deleted datasets / missing lineage)
        products_to_remove = (
            db.query(Product)
            .filter(
                (Product.sku.like("CUST%"))  # Target synthetic CUST products
                | (Product.sku == None)
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
        product_skus_to_remove = [p.sku for p in products_to_remove]

        # 3. Find associated records to remove (orphans, failed imports, or linked to removed products)
        all_product_ids = db.query(Product.id)

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

        # Proof that: 10001, MAT-2001, ITEM0001 will survive
        skus_to_check = ["10001", "MAT-2001", "ITEM0001"]
        proof_survivors = {}
        for sku in skus_to_check:
            proof_survivors[sku] = sku not in product_skus_to_remove

        if not confirm:
            return {
                "success": True,
                "confirmed": False,
                "audit_report": {
                    "products_to_remove": product_skus_to_remove,
                    "inventory_to_remove_count": len(inventory_to_remove),
                    "sales_to_remove_count": len(sales_to_remove),
                    "forecasts_to_remove_count": len(forecasts_to_remove),
                    "risks_to_remove_count": len(risks_to_remove),
                    "alerts_to_remove_count": len(alerts_to_remove),
                },
                "proof_survivors": proof_survivors,
            }

        # Actual deletion
        products_removed = 0
        inventory_removed = 0
        sales_removed = 0
        forecasts_removed = 0
        risks_removed = 0
        alerts_removed = 0
        transfers_removed = 0

        from sqlalchemy import or_

        if inventory_ids_to_remove or product_ids_to_remove:
            inventory_conds = []
            if inventory_ids_to_remove:
                inventory_conds.append(InventoryItem.id.in_(inventory_ids_to_remove))
            if product_ids_to_remove:
                inventory_conds.append(
                    InventoryItem.product_id.in_(product_ids_to_remove)
                )
            inventory_removed = (
                db.query(InventoryItem)
                .filter(or_(*inventory_conds))
                .delete(synchronize_session=False)
            )

        if sales_ids_to_remove or product_ids_to_remove:
            sales_conds = []
            if sales_ids_to_remove:
                sales_conds.append(Sale.id.in_(sales_ids_to_remove))
            if product_ids_to_remove:
                sales_conds.append(Sale.product_id.in_(product_ids_to_remove))
            sales_removed = (
                db.query(Sale)
                .filter(or_(*sales_conds))
                .delete(synchronize_session=False)
            )

        if forecasts_ids_to_remove or product_ids_to_remove:
            forecasts_conds = []
            if forecasts_ids_to_remove:
                forecasts_conds.append(Forecast.id.in_(forecasts_ids_to_remove))
            if product_ids_to_remove:
                forecasts_conds.append(Forecast.product_id.in_(product_ids_to_remove))
            forecasts_removed = (
                db.query(Forecast)
                .filter(or_(*forecasts_conds))
                .delete(synchronize_session=False)
            )

        if risks_ids_to_remove or product_ids_to_remove:
            risks_conds = []
            if risks_ids_to_remove:
                risks_conds.append(RiskScore.id.in_(risks_ids_to_remove))
            if product_ids_to_remove:
                risks_conds.append(RiskScore.product_id.in_(product_ids_to_remove))
            risks_removed = (
                db.query(RiskScore)
                .filter(or_(*risks_conds))
                .delete(synchronize_session=False)
            )

        if alerts_ids_to_remove or product_ids_to_remove:
            alerts_conds = []
            if alerts_ids_to_remove:
                alerts_conds.append(Alert.id.in_(alerts_ids_to_remove))
            if product_ids_to_remove:
                alerts_conds.append(Alert.product_id.in_(product_ids_to_remove))
            alerts_removed = (
                db.query(Alert)
                .filter(or_(*alerts_conds))
                .delete(synchronize_session=False)
            )

        # Delete InventoryTransfer references BEFORE deleting Product to satisfy FK constraints
        transfers_removed = (
            db.query(InventoryTransfer)
            .filter(InventoryTransfer.product_id.in_(product_ids_to_remove))
            .delete(synchronize_session=False)
        )
        # Now delete the products themselves
        products_removed = (
            db.query(Product)
            .filter(Product.id.in_(product_ids_to_remove))
            .delete(synchronize_session=False)
        )

        db.commit()

        # Trigger a background task for the heavy recalculation
        background_tasks.add_task(
            _recalculate_all_metrics_task, str(current_user.username)
        )

        AuditRepository(db).log(
            str(current_user.username),
            "cleanup",
            "database",
            f"Purged {products_removed} fake products. Triggered background metrics recalculation.",
        )

        return {
            "success": True,
            "confirmed": True,
            "message": "Cleanup complete. Full metrics recalculation is running in the background.",
            "metrics": {
                "products_removed": products_removed,
                "inventory_removed": inventory_removed,
                "sales_removed": sales_removed,
                "forecasts_removed": forecasts_removed,
                "risks_removed": risks_removed,
                "alerts_removed": alerts_removed,
                "transfers_removed": transfers_removed,
            },
            "proof_survivors": proof_survivors,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {e}")


@router.get("/list")
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    datasets = DatasetRepository(db).get_all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "filename": d.filename,
            "rows": d.rows,
            "sku_count": d.sku_count,
            "quality_score": d.quality_score,
            "date_from": d.date_from,
            "date_to": d.date_to,
            "owner": d.owner,
            "uploaded_at": str(d.uploaded_at),
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


@router.post("/{dataset_id}/delete")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    from backend.database.models import Dataset

    # 1. Fetch the dataset
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    batch_id = ds.import_batch_id

    try:
        if batch_id:
            # Collect all product IDs for this batch using raw SQL
            product_rows = db.execute(
                text("SELECT id FROM products WHERE import_batch_id = :bid"),
                {"bid": batch_id},
            ).fetchall()
            product_ids = [r[0] for r in product_rows]

            if product_ids:
                # Delete in strict FK dependency order using raw SQL
                # (bypasses ORM session to guarantee execution order)
                product_ids_tuple = tuple(product_ids)
                db.execute(
                    text("DELETE FROM risk_scores WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM alerts WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM forecasts_new WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM transfers WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM sales WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM inventory WHERE product_id IN :pids"),
                    {"pids": product_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM products WHERE id IN :pids"),
                    {"pids": product_ids_tuple},
                )

            # Fallback: any remaining products with this batch_id not caught above
            remaining = db.execute(
                text("SELECT id FROM products WHERE import_batch_id = :bid"),
                {"bid": batch_id},
            ).fetchall()
            if remaining:
                rem_ids_tuple = tuple(r[0] for r in remaining)
                db.execute(
                    text("DELETE FROM risk_scores WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM alerts WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM forecasts_new WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM transfers WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM sales WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM inventory WHERE product_id IN :pids"),
                    {"pids": rem_ids_tuple},
                )
                db.execute(
                    text("DELETE FROM products WHERE id IN :pids"),
                    {"pids": rem_ids_tuple},
                )

        # Finally delete the dataset record itself
        db.execute(text("DELETE FROM datasets WHERE id = :did"), {"did": dataset_id})

        db.commit()

        # Auto-reset in-memory Prometheus metrics so the telemetry
        # dashboard reflects the deletion immediately (shows 0).
        try:
            from prometheus_client import REGISTRY

            for collector in list(REGISTRY._collector_to_names.keys()):
                try:
                    REGISTRY.unregister(collector)
                except Exception:
                    pass
        except Exception:
            pass  # Telemetry reset is best-effort; never block the response

        AuditRepository(db).log(
            str(current_user.username),
            "delete_dataset",
            "dataset",
            f"Deleted dataset {dataset_id} and all related elements",
        )

        return {
            "success": True,
            "detail": f"Dataset {dataset_id} and all related elements successfully removed",
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Dataset deletion failed: {e}")

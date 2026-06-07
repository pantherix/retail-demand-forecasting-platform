"""
Smart CSV Ingestor
==================
Accepts ANY retail CSV and converts it to the platform's canonical format:
    date, product_id, category, units_sold, stock_on_hand, unit_cost

Handles:
- Native format (already has required columns)
- Transaction-level (one row per sale: Customer ID, Quantity, Price per Unit)
- Aggregated sales (date + product + revenue/amount, no quantity)
- Wide format (dates as column headers)
- Messy column names (case-insensitive, spaces, underscores)
"""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd


# ── Column name aliases ───────────────────────────────────────────────────────
DATE_ALIASES = [
    "date", "transaction_date", "order_date", "sale_date",
    "invoice_date", "purchase_date", "day",
]

SKU_ALIASES = [
    "product_id", "sku", "item_id", "product_code", "item_code",
    "product_name", "item_name", "product", "item", "article",
    "product_category", "category", "product category",
]

SALES_ALIASES = [
    "units_sold", "quantity", "qty", "units", "sales_qty",
    "quantity_sold", "volume", "sales_volume", "amount_sold",
    "sales", "total_qty",
]

PRICE_ALIASES = [
    "unit_cost", "price_per_unit", "price", "unit_price", "cost",
    "selling_price", "mrp", "rate", "avg_price",
]

REVENUE_ALIASES = [
    "total_amount", "total", "revenue", "sales_amount",
    "total_sales", "gross_sales", "net_sales", "amount",
]

STOCK_ALIASES = [
    "stock_on_hand", "stock", "inventory", "closing_stock",
    "available_stock", "on_hand", "balance",
]

CATEGORY_ALIASES = [
    "category", "product_category", "department", "segment",
    "product category", "type", "product_type",
]


def _normalize(name: str) -> str:
    """Lowercase + strip + collapse spaces/underscores."""
    return re.sub(r"[\s_]+", "_", name.strip().lower())


def _find_column(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    """Return the first DataFrame column that matches any alias."""
    norm_map = {_normalize(c): c for c in df.columns}
    for alias in aliases:
        if _normalize(alias) in norm_map:
            return norm_map[_normalize(alias)]
    return None


def _detect_format(df: pd.DataFrame) -> str:
    """
    Returns one of:
      'native'      - already has required columns
      'transaction' - one row per customer purchase
      'aggregated'  - daily sales by product but uses revenue not qty
      'unknown'     - can't determine
    """
    has_date  = _find_column(df, DATE_ALIASES)
    has_sku   = _find_column(df, SKU_ALIASES)
    has_sales = _find_column(df, SALES_ALIASES)
    has_stock = _find_column(df, STOCK_ALIASES)

    if has_date and has_sku and has_sales and has_stock:
        return "native"
    if has_date and has_sku and has_sales:
        return "transaction"
    if has_date and has_sku and _find_column(df, REVENUE_ALIASES):
        return "aggregated"
    return "unknown"


def _synthetic_stock(daily_sales: pd.Series, reorder_threshold: float = 0.3) -> pd.Series:
    """
    Generate plausible stock_on_hand values from a sales series.
    Starts at 30x avg daily sales, depletes daily, auto-replenishes.
    """
    avg   = daily_sales.mean()
    stock = float(avg * 30)
    stocks = []
    for sale in daily_sales:
        stock = max(stock - sale, 0)
        if stock < avg * reorder_threshold * 30:
            stock += avg * 20   # replenishment event
        stocks.append(round(stock, 0))
    return pd.Series(stocks, index=daily_sales.index)


def ingest(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Convert any input DataFrame to the platform's canonical format.

    Returns
    -------
    canonical_df : pd.DataFrame
        Columns: date, product_id, category, units_sold,
                 stock_on_hand, reorder_qty, promotion, holiday, unit_cost
    meta : dict
        Info about what was detected and mapped.
    """
    fmt  = _detect_format(df)
    meta = {"format_detected": fmt, "original_rows": len(df), "original_cols": list(df.columns)}

    if fmt == "native":
        out = _ingest_native(df)

    elif fmt == "transaction":
        out = _ingest_transaction(df)

    elif fmt == "aggregated":
        out = _ingest_aggregated(df)

    else:
        # Last resort: try to find at least a date and numeric column
        out = _ingest_best_effort(df)

    out = out.sort_values(["product_id", "date"]).reset_index(drop=True)
    meta["output_rows"] = len(out)
    meta["skus"]        = sorted(out["product_id"].unique().tolist())
    meta["sku_count"]   = len(meta["skus"])
    meta["date_range"]  = f"{out['date'].min().date()} → {out['date'].max().date()}"
    return out, meta


# ── Format handlers ───────────────────────────────────────────────────────────

def _ingest_native(df: pd.DataFrame) -> pd.DataFrame:
    """Already correct format — just normalize column names."""
    mapping = {}
    for target, aliases in [
        ("date",         DATE_ALIASES),
        ("product_id",   SKU_ALIASES),
        ("category",     CATEGORY_ALIASES),
        ("units_sold",   SALES_ALIASES),
        ("stock_on_hand",STOCK_ALIASES),
        ("unit_cost",    PRICE_ALIASES),
    ]:
        col = _find_column(df, aliases)
        if col:
            mapping[col] = target

    out = df.rename(columns=mapping).copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"])

    # Ensure ID and Category are strings to avoid mixed-type issues
    if "product_id" in out.columns:
        out["product_id"] = out["product_id"].astype(str)
    if "category" in out.columns:
        out["category"] = out["category"].astype(str)

    for col, default in [("reorder_qty", 0), ("promotion", 0), ("holiday", 0)]:
        if col not in out.columns:
            out[col] = default

    if "category" not in out.columns:
        out["category"] = "General"
    if "unit_cost" not in out.columns:
        out["unit_cost"] = 1.0

    return out[["date","product_id","category","units_sold",
                "stock_on_hand","reorder_qty","promotion","holiday","unit_cost"]]


def _ingest_transaction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transaction-level data (e.g. Kaggle retail sales dataset).
    Groups by date + product, sums quantity, derives stock synthetically.
    """
    date_col  = _find_column(df, DATE_ALIASES)
    qty_col   = _find_column(df, SALES_ALIASES)
    price_col = _find_column(df, PRICE_ALIASES)
    cat_col   = _find_column(df, CATEGORY_ALIASES)

    # For SKU, prefer columns that look like ID/code, not category
    sku_col = _find_column(df, [
        "product_id", "sku", "item_id", "product_code", "item_code",
        "product_name", "item_name", "product", "item", "article",
    ])
    # Use category as SKU source only if no dedicated SKU column
    sku_source = sku_col if sku_col else cat_col

    keep_cols = list({c for c in [date_col, sku_source, qty_col, price_col, cat_col] if c})
    work = df[keep_cols].copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work[qty_col]  = pd.to_numeric(work[qty_col],  errors="coerce").fillna(0)

    if price_col:
        work[price_col] = pd.to_numeric(work[price_col], errors="coerce").fillna(1.0)

    agg = {qty_col: "sum"}
    if price_col:
        agg[price_col] = "mean"
    # Only include cat_col in agg if it's different from sku_source
    if cat_col and cat_col != sku_source and cat_col in work.columns:
        agg[cat_col] = "first"

    daily = (
        work.groupby([date_col, sku_source])
        .agg(agg)
        .reset_index()
    )

    rows = []
    for sku, grp in daily.groupby(sku_source):
        grp = grp.sort_values(date_col).reset_index(drop=True)

        # Fill missing dates
        full_range = pd.date_range(grp[date_col].min(), grp[date_col].max(), freq="D")
        grp = grp.set_index(date_col).reindex(full_range).reset_index()
        grp.rename(columns={"index": date_col}, inplace=True)

        # Fill numeric gaps with 0, but keep string IDs as-is (they are handled via loop variables)
        num_cols = [qty_col]
        if price_col and price_col in grp.columns:
            num_cols.append(price_col)
        grp[num_cols] = grp[num_cols].fillna(0)

        sales_series = grp[qty_col].astype(float)
        stock_series = _synthetic_stock(sales_series)

        unit_cost = float(grp[price_col].mean()) if price_col and price_col in grp.columns else 1.0

        # Determine category
        if cat_col and cat_col != sku_source and cat_col in grp.columns:
            vals = grp[cat_col].dropna()
            category = str(vals.mode()[0]) if len(vals) > 0 else str(sku)
        else:
            # sku_source IS the category column
            category = str(sku)

        # Clean product_id from the SKU value
        product_id = re.sub(r"[^A-Za-z0-9\-]", "", str(sku).upper().replace(" ", "-"))[:20]

        for i, row in grp.iterrows():
            rows.append({
                "date":         row[date_col],
                "product_id":   product_id,
                "category":     category,
                "units_sold":   max(0, float(row[qty_col])),
                "stock_on_hand":float(stock_series.iloc[i]),
                "reorder_qty":  0,
                "promotion":    0,
                "holiday":      0,
                "unit_cost":    round(unit_cost, 2),
            })

    return pd.DataFrame(rows)


def _ingest_aggregated(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue-only data — estimate units from revenue / avg price."""
    date_col    = _find_column(df, DATE_ALIASES)
    sku_col     = _find_column(df, SKU_ALIASES)
    rev_col     = _find_column(df, REVENUE_ALIASES)
    price_col   = _find_column(df, PRICE_ALIASES)
    cat_col     = _find_column(df, CATEGORY_ALIASES)

    work = df.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=[date_col])
    work[rev_col]  = pd.to_numeric(work[rev_col], errors="coerce").fillna(0)

    avg_price = 100.0
    if price_col:
        work[price_col] = pd.to_numeric(work[price_col], errors="coerce").fillna(100)
        avg_price = work[price_col].mean()

    work["_units"] = (work[rev_col] / max(avg_price, 1)).round(0)

    # Delegate to transaction handler with units column
    work_renamed = work.rename(columns={
        date_col: "date",
        sku_col:  "product_id",
        "_units": "units_sold",
    })
    if price_col:
        work_renamed = work_renamed.rename(columns={price_col: "unit_cost"})
    if cat_col:
        work_renamed = work_renamed.rename(columns={cat_col: "category"})

    return _ingest_transaction(work_renamed)


def _ingest_best_effort(df: pd.DataFrame) -> pd.DataFrame:
    """
    Last resort: find any date column and any numeric column,
    treat numeric as daily sales for a single SKU.
    """
    date_col = None
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() > len(df) * 0.5:
                date_col = col
                break
        except Exception:
            continue

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if not date_col or not numeric_cols:
        raise ValueError(
            "Could not detect a date column or numeric sales column. "
            "Please ensure your file has at least a date column and a quantity/sales column."
        )

    sales_col = numeric_cols[0]
    work = pd.DataFrame({
        "date":      pd.to_datetime(df[date_col], errors="coerce"),
        "units_sold": pd.to_numeric(df[sales_col], errors="coerce").fillna(0),
    }).dropna(subset=["date"])

    work["product_id"]   = "SKU-001"
    work["category"]     = "General"
    work["stock_on_hand"]= _synthetic_stock(work["units_sold"])
    work["reorder_qty"]  = 0
    work["promotion"]    = 0
    work["holiday"]      = 0
    work["unit_cost"]    = 1.0

    return work[["date","product_id","category","units_sold",
                 "stock_on_hand","reorder_qty","promotion","holiday","unit_cost"]]


def preview_mapping(df: pd.DataFrame) -> dict:
    """Return what columns were detected without transforming data."""
    return {
        "format":    _detect_format(df),
        "date":      _find_column(df, DATE_ALIASES),
        "product":   _find_column(df, SKU_ALIASES),
        "sales_qty": _find_column(df, SALES_ALIASES),
        "price":     _find_column(df, PRICE_ALIASES),
        "revenue":   _find_column(df, REVENUE_ALIASES),
        "stock":     _find_column(df, STOCK_ALIASES),
        "category":  _find_column(df, CATEGORY_ALIASES),
    }

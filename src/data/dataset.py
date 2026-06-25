from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = ROOT / "data" / "retail_sales_sample.csv"


def load_retail_data(path: Path | str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {data_path}. "
            "Run scripts/generate_sample_data.py first."
        )

    df = pd.read_csv(data_path, parse_dates=["date"])

    # Ensure ID and Category are strings
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    if "category" in df.columns:
        df["category"] = df["category"].astype(str)
    required = {
        "date",
        "product_id",
        "category",
        "units_sold",
        "stock_on_hand",
        "reorder_qty",
        "promotion",
        "holiday",
        "unit_cost",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    return df.sort_values(["product_id", "date"]).reset_index(drop=True)


def product_series(df: pd.DataFrame, product_id: str) -> pd.Series:
    product_df = df[df["product_id"] == product_id].sort_values("date")
    if product_df.empty:
        raise ValueError(f"Unknown product_id: {product_id}")
    return product_df.set_index("date")["units_sold"].astype(float)


def latest_inventory(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values("date")
        .groupby("product_id", as_index=False)
        .tail(1)
        .sort_values("product_id")
        .reset_index(drop=True)
    )

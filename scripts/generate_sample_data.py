from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "retail_sales_sample.csv"


def build_product_series(
    rng: np.random.Generator,
    product_id: str,
    category: str,
    base_demand: float,
    trend: float,
    promo_lift: float,
    unit_cost: float,
    starting_stock: int,
    days: int = 240,
) -> pd.DataFrame:
    dates = pd.date_range("2025-01-01", periods=days, freq="D")
    rows = []
    stock_on_hand = starting_stock

    for idx, date in enumerate(dates):
        weekly = 1.0 + 0.18 * np.sin(2 * np.pi * idx / 7)
        monthly = 1.0 + 0.10 * np.sin(2 * np.pi * idx / 30)
        promotion = int(idx % 41 in {0, 1, 2, 3})
        holiday = int(date.month == 12 or (date.month == 8 and date.day in {14, 15, 16}))
        noise = rng.normal(0, base_demand * 0.08)
        demand = base_demand * weekly * monthly + trend * idx + promotion * promo_lift + holiday * base_demand * 0.25 + noise
        units_sold = max(0, int(round(demand)))

        reorder_qty = 0
        if stock_on_hand < base_demand * 7:
            reorder_qty = int(base_demand * 21)

        stock_on_hand = max(0, stock_on_hand + reorder_qty - units_sold)

        rows.append(
            {
                "date": date.date().isoformat(),
                "product_id": product_id,
                "category": category,
                "units_sold": units_sold,
                "stock_on_hand": stock_on_hand,
                "reorder_qty": reorder_qty,
                "promotion": promotion,
                "holiday": holiday,
                "unit_cost": round(unit_cost, 2),
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    rng = np.random.default_rng(42)
    products = [
        ("SKU-101", "Beverages", 84, 0.03, 38, 1.8, 1800),
        ("SKU-205", "Snacks", 62, 0.01, 25, 1.2, 1250),
        ("SKU-330", "Personal Care", 35, 0.04, 16, 3.4, 900),
        ("SKU-440", "Home Care", 48, -0.01, 19, 2.7, 1150),
        ("SKU-555", "Packaged Food", 95, 0.05, 45, 2.1, 2100),
    ]

    frames = [
        build_product_series(rng, product_id, category, base, trend, lift, cost, stock)
        for product_id, category, base, trend, lift, cost, stock in products
    ]
    df = pd.concat(frames, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Generated {len(df):,} rows at {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

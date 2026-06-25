from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.data.dataset import load_retail_data, product_series
from src.models.baseline import benchmark_product

REPORT_PATH = ROOT / "reports" / "model_leaderboard.csv"


def main() -> None:
    df = load_retail_data()
    rows = []

    for product_id in sorted(df["product_id"].unique()):
        series = product_series(df, product_id)
        series.name = product_id
        for result in benchmark_product(series, horizon=30):
            rows.append(
                {
                    "product_id": product_id,
                    "model_name": result.model_name,
                    "mae": result.mae,
                    "rmse": result.rmse,
                    "mape": result.mape,
                }
            )

    leaderboard = pd.DataFrame(rows).sort_values(["product_id", "rmse"])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    leaderboard.to_csv(REPORT_PATH, index=False)
    print(leaderboard)
    print(f"Saved leaderboard at {REPORT_PATH}")


if __name__ == "__main__":
    main()

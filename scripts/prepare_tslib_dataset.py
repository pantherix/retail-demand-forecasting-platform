from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.data.dataset import load_retail_data

OUTPUT_DIR = ROOT / "data" / "tslib"


def main() -> None:
    df = load_retail_data()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for product_id in sorted(df["product_id"].unique()):
        product_df = df[df["product_id"] == product_id].sort_values("date")
        tslib_df = product_df[["date", "units_sold"]].rename(columns={"date": "date"})
        output_path = OUTPUT_DIR / f"{product_id}.csv"
        tslib_df.to_csv(output_path, index=False)
        print(f"Prepared {output_path}")


if __name__ == "__main__":
    main()

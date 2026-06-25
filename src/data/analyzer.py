from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


class GenericAnalyzer:
    """Analyzes any DataFrame and extracts domain-agnostic insights."""

    @staticmethod
    def analyze(df: pd.DataFrame) -> Dict[str, Any]:
        report = {
            "overview": {
                "rows": len(df),
                "columns": len(df.columns),
                "total_cells": len(df) * len(df.columns),
                "missing_cells": int(df.isnull().sum().sum()),
                "missing_pct": (
                    round(
                        (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100, 2
                    )
                    if len(df) > 0
                    else 0
                ),
                "duplicate_rows": int(df.duplicated().sum()),
                "memory_usage": (
                    f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
                ),
            },
            "columns": {},
            "correlations": [],
            "time_insights": None,
        }

        for col in df.columns:
            col_data = df[col]
            dtype = str(col_data.dtype)

            c_report = {
                "name": col,
                "type": dtype,
                "missing": int(col_data.isnull().sum()),
                "missing_pct": round((col_data.isnull().sum() / len(df)) * 100, 2),
                "unique": int(col_data.nunique()),
            }

            if pd.api.types.is_numeric_dtype(col_data.dtype):
                c_report["kind"] = "numerical"
                c_report["stats"] = {
                    "mean": float(col_data.mean()) if not col_data.empty else 0,
                    "std": float(col_data.std()) if not col_data.empty else 0,
                    "min": float(col_data.min()) if not col_data.empty else 0,
                    "max": float(col_data.max()) if not col_data.empty else 0,
                    "median": float(col_data.median()) if not col_data.empty else 0,
                }
                if len(col_data.dropna()) > 10 and c_report["stats"]["std"] > 0:
                    z_scores = np.abs(
                        (col_data - c_report["stats"]["mean"])
                        / c_report["stats"]["std"]
                    )
                    c_report["outliers"] = int((z_scores > 3).sum())
                else:
                    c_report["outliers"] = 0

            elif pd.api.types.is_datetime64_any_dtype(col_data.dtype):
                c_report["kind"] = "datetime"
                c_report["range"] = {
                    "min": str(col_data.min()),
                    "max": str(col_data.max()),
                }

            else:
                c_report["kind"] = "categorical"
                top_values = col_data.value_counts().head(5).to_dict()
                c_report["top_values"] = [
                    {"label": str(k), "count": int(v)} for k, v in top_values.items()
                ]

            report["columns"][col] = c_report

        num_df = df.select_dtypes(include=[np.number])
        if len(num_df.columns) > 1:
            corr_matrix = num_df.corr().round(2)
            for i in range(len(corr_matrix.columns)):
                for j in range(i + 1, len(corr_matrix.columns)):
                    val = corr_matrix.iloc[i, j]
                    if not np.isnan(val):
                        report["correlations"].append(
                            {
                                "col1": corr_matrix.columns[i],
                                "col2": corr_matrix.columns[j],
                                "score": float(val),
                            }
                        )
            report["correlations"].sort(key=lambda x: abs(x["score"]), reverse=True)

        date_cols = [
            c for c, v in report["columns"].items() if v.get("kind") == "datetime"
        ]
        if date_cols:
            date_col = date_cols[0]
            report["time_insights"] = {
                "column": date_col,
                "span_days": (df[date_col].max() - df[date_col].min()).days,
            }

        return report

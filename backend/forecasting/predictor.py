from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd


class ForecastPredictor:
    """Loads a trained SKU model and produces multi-step forecasts."""

    def __init__(self, model_dir: str = "artifacts/models"):
        self.model_dir = Path(model_dir)

    def _load_model(self, sku: str):
        model_path = self.model_dir / f"{sku}.joblib"
        if not model_path.exists():
            return None
        return joblib.load(model_path)

    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        data = df.copy()
        data["lag_1"] = data["sales"].shift(1)
        data["lag_7"] = data["sales"].shift(7)
        data["lag_14"] = data["sales"].shift(14)
        data["lag_30"] = data["sales"].shift(30)
        data["rolling_mean_7"] = data["sales"].rolling(7).mean()
        data["rolling_mean_30"] = data["sales"].rolling(30).mean()
        data["rolling_std_7"] = data["sales"].rolling(7).std()
        data["day_of_week"] = pd.to_datetime(data["date"]).dt.dayofweek
        data["month"] = pd.to_datetime(data["date"]).dt.month
        data["quarter"] = pd.to_datetime(data["date"]).dt.quarter
        return data.dropna()

    FEATURE_COLUMNS = [
        "lag_1", "lag_7", "lag_14", "lag_30",
        "rolling_mean_7", "rolling_mean_30", "rolling_std_7",
        "day_of_week", "month", "quarter",
    ]

    def forecast_horizon(self, sku: str, df: pd.DataFrame, horizon: int = 30) -> Dict:
        """Return day-by-day forecasts for the given horizon using the last known row."""
        model = self._load_model(sku)

        # Fall back to a simple moving average when no trained model exists
        if model is None:
            avg = float(df["sales"].tail(30).mean()) if "sales" in df.columns else 100.0
            forecasts = [{"day": i + 1, "forecast": round(avg, 2)} for i in range(horizon)]
            return {
                "sku": sku,
                "horizon": horizon,
                "model": "moving_average_fallback",
                "forecasts": forecasts,
                "total_forecast": round(avg * horizon, 2),
            }

        data = self._build_features(df)
        last_row = data.iloc[-1][self.FEATURE_COLUMNS].values.reshape(1, -1)
        raw_pred = float(model.predict(last_row)[0])

        forecasts = []
        for i in range(horizon):
            # Simple decay: use same prediction for now (model was trained on point predictions)
            forecasts.append({"day": i + 1, "forecast": round(max(0.0, raw_pred), 2)})

        return {
            "sku": sku,
            "horizon": horizon,
            "model": "xgboost",
            "forecasts": forecasts,
            "total_forecast": round(raw_pred * horizon, 2),
        }

    def confidence_interval(self, forecasts: List[float], z: float = 1.96) -> Dict:
        arr = np.array(forecasts)
        mean = float(np.mean(arr))
        std = float(np.std(arr)) if len(arr) > 1 else 0.0
        return {
            "mean": round(mean, 2),
            "lower": round(mean - z * std, 2),
            "upper": round(mean + z * std, 2),
        }


class ModelRegistry:
    """File-backed registry that persists model metadata per SKU."""

    def __init__(self, registry_path: str = "artifacts/registry"):
        self.registry = Path(registry_path)
        self.registry.mkdir(parents=True, exist_ok=True)

    def register(self, sku: str, model_name: str, metrics: Dict):
        payload = {"sku": sku, "model": model_name, "metrics": metrics}
        with open(self.registry / f"{sku}.json", "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=4)

    def load(self, sku: str):
        file = self.registry / f"{sku}.json"
        if not file.exists():
            return None
        with open(file, "r", encoding="utf-8") as fp:
            return json.load(fp)

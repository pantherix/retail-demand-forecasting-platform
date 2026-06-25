from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)


class ForecastTrainingException(Exception):
    pass


class ForecastTrainer:

    def __init__(self, model_dir: str = "artifacts/models"):

        self.model_dir = Path(model_dir)

        self.model_dir.mkdir(parents=True, exist_ok=True)

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:

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

    def train_xgboost(self, df: pd.DataFrame, sku: str) -> Dict:

        data = self.build_features(df)

        feature_columns = [
            "lag_1",
            "lag_7",
            "lag_14",
            "lag_30",
            "rolling_mean_7",
            "rolling_mean_30",
            "rolling_std_7",
            "day_of_week",
            "month",
            "quarter",
        ]

        X = data[feature_columns]

        y = data["sales"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )

        model = XGBRegressor(
            n_estimators=500,
            learning_rate=0.03,
            max_depth=8,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        )

        model.fit(X_train, y_train)

        predictions = model.predict(X_test)

        rmse = np.sqrt(mean_squared_error(y_test, predictions))

        mae = mean_absolute_error(y_test, predictions)

        artifact_path = self.model_dir / f"{sku}.joblib"

        joblib.dump(model, artifact_path)

        metrics = {
            "sku": sku,
            "rmse": float(rmse),
            "mae": float(mae),
            "samples": len(df),
            "features": len(feature_columns),
            "model_path": str(artifact_path),
        }

        metrics_file = self.model_dir / f"{sku}_metrics.json"

        with open(metrics_file, "w", encoding="utf-8") as fp:

            json.dump(metrics, fp, indent=4)

        logger.info("Training complete " "for %s", sku)

        return metrics

    def batch_train(self, files: List[str]) -> Dict:

        results = {}

        for file in files:

            path = Path(file)

            sku = path.stem

            df = pd.read_csv(path)

            metrics = self.train_xgboost(df, sku)

            results[sku] = metrics

        return results

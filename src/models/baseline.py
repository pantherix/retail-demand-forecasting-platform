from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error


@dataclass
class ForecastResult:
    product_id: str
    model_name: str
    horizon: int
    forecast: list[float]
    mae: float
    rmse: float
    mape: float


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    safe_denominator = np.where(y_true == 0, 1, y_true)
    return float(np.mean(np.abs((y_true - y_pred) / safe_denominator)) * 100)


def seasonal_naive_forecast(series: pd.Series, horizon: int, season_length: int = 7) -> list[float]:
    values = series.to_numpy(dtype=float)
    if len(values) < season_length:
        return [float(np.mean(values))] * horizon

    pattern = values[-season_length:]
    return [float(pattern[idx % season_length]) for idx in range(horizon)]


def moving_average_forecast(series: pd.Series, horizon: int, window: int = 14) -> list[float]:
    values = series.to_numpy(dtype=float)
    avg = float(np.mean(values[-window:]))
    return [avg] * horizon


def random_forest_forecast(series: pd.Series, horizon: int, lags: int = 14) -> list[float]:
    values = series.to_numpy(dtype=float)
    if len(values) <= lags + 5:
        return moving_average_forecast(series, horizon)

    x_rows, y_rows = [], []
    for idx in range(lags, len(values)):
        x_rows.append(values[idx - lags : idx])
        y_rows.append(values[idx])

    model = RandomForestRegressor(n_estimators=120, random_state=42, min_samples_leaf=2)
    model.fit(np.array(x_rows), np.array(y_rows))

    history = list(values[-lags:])
    preds = []
    for _ in range(horizon):
        pred = float(model.predict(np.array(history[-lags:]).reshape(1, -1))[0])
        preds.append(max(0.0, pred))
        history.append(pred)
    return preds


def evaluate_model(series: pd.Series, model_name: str, horizon: int = 30) -> ForecastResult:
    if len(series) <= horizon + 20:
        raise ValueError("Need more history for evaluation.")

    train = series.iloc[:-horizon]
    test = series.iloc[-horizon:]

    if model_name == "SeasonalNaive":
        preds = seasonal_naive_forecast(train, horizon)
    elif model_name == "MovingAverage":
        preds = moving_average_forecast(train, horizon)
    elif model_name == "RandomForest":
        preds = random_forest_forecast(train, horizon)
    else:
        raise ValueError(f"Unsupported model: {model_name}")

    y_true = test.to_numpy(dtype=float)
    y_pred = np.array(preds)
    return ForecastResult(
        product_id=str(series.name or "unknown"),
        model_name=model_name,
        horizon=horizon,
        forecast=[round(float(v), 2) for v in preds],
        mae=round(float(mean_absolute_error(y_true, y_pred)), 3),
        rmse=round(float(mean_squared_error(y_true, y_pred) ** 0.5), 3),
        mape=round(_mape(y_true, y_pred), 3),
    )


def benchmark_product(series: pd.Series, horizon: int = 30) -> list[ForecastResult]:
    return [
        evaluate_model(series, "SeasonalNaive", horizon),
        evaluate_model(series, "MovingAverage", horizon),
        evaluate_model(series, "RandomForest", horizon),
    ]


def forecast_with_best_model(series: pd.Series, horizon: int = 30) -> ForecastResult:
    leaderboard = benchmark_product(series, horizon=min(horizon, 30))
    best = min(leaderboard, key=lambda item: item.rmse)

    if best.model_name == "SeasonalNaive":
        forecast = seasonal_naive_forecast(series, horizon)
    elif best.model_name == "MovingAverage":
        forecast = moving_average_forecast(series, horizon)
    else:
        forecast = random_forest_forecast(series, horizon)

    return ForecastResult(
        product_id=str(series.name or "unknown"),
        model_name=best.model_name,
        horizon=horizon,
        forecast=[round(float(v), 2) for v in forecast],
        mae=best.mae,
        rmse=best.rmse,
        mape=best.mape,
    )

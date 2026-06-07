"""Tests for forecasting models."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models.baseline import (
    seasonal_naive_forecast,
    moving_average_forecast,
    random_forest_forecast,
    evaluate_model,
    forecast_with_best_model,
    ForecastResult,
)


@pytest.fixture
def sample_series() -> pd.Series:
    np.random.seed(42)
    values = 100 + np.cumsum(np.random.randn(120))
    values = np.maximum(values, 10)
    return pd.Series(values.tolist(), name="SKU-TEST")


# ── Seasonal Naive ────────────────────────────────────────────────────────────
class TestSeasonalNaive:
    def test_returns_correct_length(self, sample_series):
        preds = seasonal_naive_forecast(sample_series, horizon=30)
        assert len(preds) == 30

    def test_repeats_weekly_pattern(self, sample_series):
        preds = seasonal_naive_forecast(sample_series, horizon=14, season_length=7)
        assert preds[0] == preds[7]
        assert preds[1] == preds[8]

    def test_all_non_negative(self, sample_series):
        preds = seasonal_naive_forecast(sample_series, horizon=30)
        assert all(v >= 0 for v in preds)

    def test_short_series_fallback(self):
        short = pd.Series([10.0, 20.0, 15.0])
        preds = seasonal_naive_forecast(short, horizon=5, season_length=7)
        assert len(preds) == 5


# ── Moving Average ────────────────────────────────────────────────────────────
class TestMovingAverage:
    def test_returns_correct_length(self, sample_series):
        preds = moving_average_forecast(sample_series, horizon=30)
        assert len(preds) == 30

    def test_constant_prediction(self, sample_series):
        preds = moving_average_forecast(sample_series, horizon=10)
        assert len(set(round(p, 6) for p in preds)) == 1

    def test_close_to_recent_mean(self, sample_series):
        preds = moving_average_forecast(sample_series, horizon=1, window=14)
        expected = float(np.mean(sample_series.values[-14:]))
        assert abs(preds[0] - expected) < 0.01


# ── Random Forest ─────────────────────────────────────────────────────────────
class TestRandomForest:
    def test_returns_correct_length(self, sample_series):
        preds = random_forest_forecast(sample_series, horizon=30)
        assert len(preds) == 30

    def test_all_non_negative(self, sample_series):
        preds = random_forest_forecast(sample_series, horizon=30)
        assert all(v >= 0 for v in preds)

    def test_short_series_fallback(self):
        short = pd.Series(list(range(10)), dtype=float)
        preds = random_forest_forecast(short, horizon=5)
        assert len(preds) == 5


# ── Evaluate Model ────────────────────────────────────────────────────────────
class TestEvaluateModel:
    def test_returns_forecast_result(self, sample_series):
        result = evaluate_model(sample_series, "MovingAverage", horizon=30)
        assert isinstance(result, ForecastResult)

    def test_metrics_are_non_negative(self, sample_series):
        result = evaluate_model(sample_series, "SeasonalNaive", horizon=30)
        assert result.mae >= 0
        assert result.rmse >= 0
        assert result.mape >= 0

    def test_forecast_length_matches_horizon(self, sample_series):
        result = evaluate_model(sample_series, "RandomForest", horizon=14)
        assert len(result.forecast) == 14

    def test_raises_on_insufficient_data(self):
        short = pd.Series(list(range(20)), dtype=float)
        with pytest.raises(ValueError):
            evaluate_model(short, "MovingAverage", horizon=30)


# ── Auto Best Model ───────────────────────────────────────────────────────────
class TestForecastWithBestModel:
    def test_returns_forecast_result(self, sample_series):
        result = forecast_with_best_model(sample_series, horizon=30)
        assert isinstance(result, ForecastResult)

    def test_model_name_is_valid(self, sample_series):
        result = forecast_with_best_model(sample_series, horizon=30)
        assert result.model_name in ("SeasonalNaive", "MovingAverage", "RandomForest")

    def test_forecast_length(self, sample_series):
        result = forecast_with_best_model(sample_series, horizon=21)
        assert len(result.forecast) == 21

    def test_rmse_is_best_among_models(self, sample_series):
        from src.models.baseline import benchmark_product
        best   = forecast_with_best_model(sample_series, horizon=30)
        bench  = benchmark_product(sample_series, horizon=30)
        min_rmse = min(r.rmse for r in bench)
        assert abs(best.rmse - min_rmse) < 0.001

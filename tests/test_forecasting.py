from datetime import datetime, timedelta

import pandas as pd
import pytest


# Mock structure representing your forecasting engine's intake
def preprocess_forecast_data(df: pd.DataFrame) -> pd.DataFrame:
    """The function we are testing. It must pass all rigorous edge cases."""
    if df.empty:
        raise ValueError("Cannot process an empty historical dataframe.")

    if "sales" not in df.columns or "date" not in df.columns:
        raise KeyError("Required feature columns 'sales' or 'date' are missing.")

    # Check for NaN/Null values and fix them securely (AI often forgets this)
    df = df.copy()
    df["sales"] = df["sales"].fillna(0.0)

    # Bound the values to protect machine learning matrix overflow
    df["sales"] = df["sales"].clip(lower=0.0)

    return df


# === QUALITY TESTS ===


def test_happy_path():
    """Validates basic operational correctness."""
    data = pd.DataFrame({"date": [datetime.now()], "sales": [150.0]})
    result = preprocess_forecast_data(data)
    assert len(result) == 1
    assert result["sales"].iloc[0] == 150.0


def test_empty_dataframe_edge_case():
    """Prevents backend server crashes when a retail store has no transactional history."""
    empty_df = pd.DataFrame()
    with pytest.raises(
        ValueError, match="Cannot process an empty historical dataframe."
    ):
        preprocess_forecast_data(empty_df)


def test_missing_required_columns():
    """Catches architectural drift where database schema changes break model assumptions."""
    broken_df = pd.DataFrame({"revenue": [100.0], "timestamp": [datetime.now()]})
    with pytest.raises(KeyError):
        preprocess_forecast_data(broken_df)


def test_null_and_negative_data_resilience():
    """Forces the system to gracefully clean corrupted inputs instead of breaking ML models."""
    corrupted_data = pd.DataFrame(
        {
            "date": [datetime.now(), datetime.now() + timedelta(days=1)],
            "sales": [None, -50.0],  # Missing data and physically impossible sales
        }
    )
    result = preprocess_forecast_data(corrupted_data)
    assert result["sales"].iloc[0] == 0.0  # Null handled cleanly
    assert result["sales"].iloc[1] == 0.0  # Negative clipped to logical bound

"""
Unit tests for compute_metrics_for_prices.

Creates a synthetic contiguous daily closing price series and asserts:
- returned DataFrame has the expected columns
- rolling metric columns contain no nulls (sufficient history)
- row count equals original_length - 60 (because vol60 requires 60 prior rows)
"""
import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

from app.services.analytics import compute_metrics_for_prices, calculate_metrics


def test_compute_metrics_for_synthetic_series():
    # create synthetic daily close prices (deterministic)
    L = 130  # total days; must be > 60 so vol60/sma50 can be computed
    dates = pd.date_range(start="2020-01-01", periods=L, freq="D")
    # simple steadily increasing price series (no zeros)
    closes = 100.0 + np.arange(L) * 0.5
    df = pd.DataFrame({"date": dates, "close": closes})

    result = compute_metrics_for_prices(df)

    # expected columns
    expected_cols = {"date", "return", "vol20", "vol60", "sma20", "sma50", "sharpe20", "sharpe60"}
    assert expected_cols.issubset(set(result.columns))

    # expected row count: rows with sufficient history for vol60 (min_periods=60, closed='left')
    assert len(result) == L - 60

    # rolling metric columns should have no nulls in the returned frame
    rolling_cols = ["vol20", "vol60", "sma20", "sma50", "sharpe20", "sharpe60"]
    assert not result[rolling_cols].isnull().any().any()

    # returns should also be present (not-null) for the returned rows
    assert not result["return"].isnull().any()


def test_calculate_metrics():
    # Sample data for testing
    sample_data = {
        "ticker": "AAPL",
        "prices": [150, 152, 153, 155, 154],
    }

    expected_metrics = {
        "average_price": 152.8,
        "max_price": 155,
        "min_price": 150,
    }

    # Call the function to test
    metrics = calculate_metrics(sample_data["prices"])

    # Assertions to verify the correctness of the function
    assert metrics["average_price"] == expected_metrics["average_price"]
    assert metrics["max_price"] == expected_metrics["max_price"]
    assert metrics["min_price"] == expected_metrics["min_price"]


def test_calculate_metrics_empty_data():
    with pytest.raises(HTTPException) as exc_info:
        calculate_metrics([])
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Price data cannot be empty."
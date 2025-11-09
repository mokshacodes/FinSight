"""
Analytics helpers for FinSight.

Provides functions to compute time-series metrics from price data using pandas.
All rolling calculations are performed with closed='left' to avoid look-ahead bias
(i.e., the value at time t uses only data strictly before t).
"""
from typing import List
import pandas as pd
import numpy as np
import yfinance as yf


def _ensure_datetime_and_sort(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """
    Ensure the DataFrame has a datetime index sorted in ascending order.

    Parameters
    - df: input DataFrame with a date column
    - date_col: name of the date column (default "date")

    Returns
    - copy of df with date column converted to pd.Timestamp and sorted ascending
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=date_col).reset_index(drop=True)
    return df


def compute_metrics_for_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute analytics metrics for a price DataFrame.

    Input:
    - df must contain at least columns: ['date', 'close'].
      'date' can be string or datetime-like. Rows should represent regular time
      series observations (e.g., daily close prices).

    Output:
    - DataFrame with columns:
      ['date', 'return', 'vol20', 'vol60', 'sma20', 'sma50', 'sharpe20', 'sharpe60']

    Implementation notes:
    - All rolling calculations use rolling(..., closed='left') to prevent look-ahead bias:
      the metric at row t uses only historical data strictly before t.
    - Rows with insufficient history for any metric are dropped (skips early rows).
    - 'return' is the simple percent change from previous close (may be NaN for first row).
    - volXX is the rolling standard deviation of returns over XX periods (unannualized).
    - smaXX is the simple moving average of close over XX periods (past values only).
    - sharpeXX is rolling mean(return)/rolling std(return) over XX periods (past values only).
    """
    required_cols: List[str] = ["date", "close"]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"input DataFrame must contain column '{c}'")

    df = _ensure_datetime_and_sort(df, "date")

    # compute simple daily returns (current vs prior)
    # this return column is aligned with the date for the current close
    df["return"] = df["close"].pct_change()

    # Rolling windows that exclude the current row to avoid look-ahead bias.
    # min_periods ensures we don't produce misleading metrics when not enough history.
    vol20 = df["return"].rolling(window=20, min_periods=20, closed="left").std()
    vol60 = df["return"].rolling(window=60, min_periods=60, closed="left").std()

    sma20 = df["close"].rolling(window=20, min_periods=20, closed="left").mean()
    sma50 = df["close"].rolling(window=50, min_periods=50, closed="left").mean()

    mean20 = df["return"].rolling(window=20, min_periods=20, closed="left").mean()
    mean60 = df["return"].rolling(window=60, min_periods=60, closed="left").mean()

    sharpe20 = mean20 / vol20
    sharpe60 = mean60 / vol60

    result = pd.DataFrame({
        "date": df["date"],
        "return": df["return"],
        "vol20": vol20,
        "vol60": vol60,
        "sma20": sma20,
        "sma50": sma50,
        "sharpe20": sharpe20,
        "sharpe60": sharpe60,
    })

    # Drop rows that don't have sufficient history for the computed metrics
    result = result.dropna(subset=["vol20", "vol60", "sma20", "sma50", "sharpe20", "sharpe60"]).reset_index(drop=True)

    return result


def fetch_ticker_data(tickers: List[str]) -> pd.DataFrame:
    data = yf.download(tickers, group_by='ticker')
    return data


def calculate_metrics(data: pd.DataFrame) -> pd.DataFrame:
    metrics = pd.DataFrame()
    metrics['Mean'] = data.mean()
    metrics['Standard Deviation'] = data.std()
    metrics['Max'] = data.max()
    metrics['Min'] = data.min()
    return metrics


def analyze_tickers(tickers: List[str]) -> pd.DataFrame:
    data = fetch_ticker_data(tickers)
    metrics = calculate_metrics(data)
    return metrics
from typing import List
import pandas as pd
import yfinance as yf

def fetch_ticker_data(tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    data = yf.download(tickers, start=start_date, end=end_date)
    return data

def calculate_metrics(data: pd.DataFrame) -> dict:
    metrics = {
        'mean': data.mean(),
        'median': data.median(),
        'std_dev': data.std(),
        'max': data.max(),
        'min': data.min()
    }
    return metrics

def analyze_tickers(tickers: List[str], start_date: str, end_date: str) -> dict:
    data = fetch_ticker_data(tickers, start_date, end_date)
    metrics = calculate_metrics(data)
    return metrics
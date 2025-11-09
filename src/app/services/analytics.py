from typing import List
import pandas as pd
import yfinance as yf

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
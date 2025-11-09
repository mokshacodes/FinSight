"""
FastAPI application for FinSight.

Defines endpoints to manage tickers, refresh price data, compute/store metrics,
and return summaries. Uses app.services.analytics for computations and app.db
for persistence.

Endpoints:
- GET  /tickers
- POST /add_ticker
- POST /refresh
- GET  /metrics?ticker=XYZ
- GET  /summary
"""
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
import pandas as pd
import yfinance as yf

# Import local modules (analytics + db helpers)
from app.services.analytics import compute_metrics_for_prices
from app.db import create_schema, upsert_prices, upsert_metrics, fetch_latest_metrics, fetch_summary, _get_conn

app = FastAPI(title="FinSight")


# Pydantic models for request/response validation
class TickerIn(BaseModel):
    ticker: str = Field(..., min_length=1, description="Ticker symbol, e.g. AAPL")


class MetricRow(BaseModel):
    ticker: str
    date: str
    return_: Optional[float] = Field(None, alias="return")
    vol20: Optional[float]
    vol60: Optional[float]
    sma20: Optional[float]
    sma50: Optional[float]
    sharpe20: Optional[float]
    sharpe60: Optional[float]


class SummaryOut(BaseModel):
    total_tickers: int
    price_rows: int
    metrics_rows: int
    earliest_price_date: Optional[str]
    latest_price_date: Optional[str]
    earliest_metric_date: Optional[str]
    latest_metric_date: Optional[str]


@app.on_event("startup")
def startup():
    """
    Ensure DB schema exists on application startup.
    """
    create_schema()


def _normalize_ticker(t: str) -> str:
    return t.strip().upper()


def _download_and_prepare_prices(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Download daily OHLCV for `ticker` using yfinance and return a DataFrame
    with columns: date, open, high, low, close, volume.

    Raises HTTPException(404) if no data is returned.
    """
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No price data for {ticker}")

    # Ensure expected columns exist
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            raise HTTPException(status_code=500, detail=f"Unexpected data format from yfinance for {ticker}")

    df = df.reset_index().rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    # Normalize date to ISO date string for DB storage
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    # Keep only necessary columns and drop rows with missing close
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
    return df


@app.get("/tickers", response_model=List[str])
def get_tickers():
    """
    Return a list of tracked tickers inferred from prices or metrics tables.
    """
    sql = """
    SELECT DISTINCT ticker FROM (
      SELECT ticker FROM prices
      UNION
      SELECT ticker FROM metrics
    ) ORDER BY ticker;
    """
    try:
        with _get_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            tickers = [r[0] for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return tickers


@app.post("/add_ticker", status_code=201)
def add_ticker(payload: TickerIn):
    """
    Add a ticker by downloading recent price history, storing prices and computed metrics.
    This both registers the ticker and seeds the DB so subsequent /refresh will include it.
    """
    ticker = _normalize_ticker(payload.ticker)
    try:
        prices_df = _download_and_prepare_prices(ticker)
        # upsert prices
        price_rows = prices_df.to_dict(orient="records")
        for r in price_rows:
            r["ticker"] = ticker
        upsert_prices(price_rows)

        # compute metrics (analytics expects date & close)
        metrics_df = compute_metrics_for_prices(prices_df[["date", "close"]])
        if not metrics_df.empty:
            metrics_df["ticker"] = ticker
            # rename "return" column to avoid Python reserved word conflicts when building mappings
            metrics_rows = []
            for _, row in metrics_df.iterrows():
                metrics_rows.append({
                    "ticker": ticker,
                    "date": row["date"].strftime("%Y-%m-%d") if not isinstance(row["date"], str) else row["date"],
                    "return": None if pd.isna(row["return"]) else float(row["return"]),
                    "vol20": None if pd.isna(row["vol20"]) else float(row["vol20"]),
                    "vol60": None if pd.isna(row["vol60"]) else float(row["vol60"]),
                    "sma20": None if pd.isna(row["sma20"]) else float(row["sma20"]),
                    "sma50": None if pd.isna(row["sma50"]) else float(row["sma50"]),
                    "sharpe20": None if pd.isna(row["sharpe20"]) else float(row["sharpe20"]),
                    "sharpe60": None if pd.isna(row["sharpe60"]) else float(row["sharpe60"]),
                })
            upsert_metrics(metrics_rows)

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # return a brief summary after adding
    return {"ok": True, "ticker": ticker, "message": "Ticker added and metrics computed"}


@app.post("/refresh")
def refresh_all(period: str = Query("2y", description="yfinance period (e.g., 1y, 2y, max)")):
    """
    Refresh data for all known tickers: for each ticker found in the DB, re-download
    recent price data, upsert prices, compute metrics and upsert metrics.
    Returns the DB summary after refresh.
    """
    # Determine tickers to refresh
    try:
        with _get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT ticker FROM prices UNION SELECT DISTINCT ticker FROM metrics ORDER BY 1;")
            tickers = [r[0] for r in cur.fetchall()]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not tickers:
        return {"ok": True, "message": "No tickers to refresh", "summary": fetch_summary().to_dict(orient="records")[0]}

    results = {"processed": 0, "errors": []}
    for ticker in tickers:
        try:
            prices_df = _download_and_prepare_prices(ticker, period=period)
            for r in prices_df.to_dict(orient="records"):
                r["ticker"] = ticker
            upsert_prices(prices_df.assign(ticker=ticker).to_dict(orient="records"))

            metrics_df = compute_metrics_for_prices(prices_df[["date", "close"]])
            if not metrics_df.empty:
                metrics_rows = []
                for _, row in metrics_df.iterrows():
                    metrics_rows.append({
                        "ticker": ticker,
                        "date": row["date"].strftime("%Y-%m-%d") if not isinstance(row["date"], str) else row["date"],
                        "return": None if pd.isna(row["return"]) else float(row["return"]),
                        "vol20": None if pd.isna row["vol20"]) else float(row["vol20"]),
                        "vol60": None if pd.isna(row["vol60"]) else float(row["vol60"]),
                        "sma20": None if pd.isna(row["sma20"]) else float(row["sma20"]),
                        "sma50": None if pd.isna(row["sma50"]) else float(row["sma50"]),
                        "sharpe20": None if pd.isna(row["sharpe20"]) else float(row["sharpe20"]),
                        "sharpe60": None if pd.isna(row["sharpe60"]) else float(row["sharpe60"]),
                    })
                upsert_metrics(metrics_rows)
            results["processed"] += 1
        except Exception as exc:
            results["errors"].append({"ticker": ticker, "error": str(exc)})

    summary = fetch_summary().to_dict(orient="records")[0]
    return {"ok": True, "results": results, "summary": summary}


@app.get("/metrics", response_model=List[MetricRow])
def get_metrics(ticker: Optional[str] = Query(None, description="Ticker to filter metrics by (optional)")):
    """
    Return the latest metrics rows. If `ticker` is provided, return latest metrics for that ticker only.
    """
    try:
        df = fetch_latest_metrics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if ticker:
        t = _normalize_ticker(ticker)
        df = df[df["ticker"].str.upper() == t]
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No metrics found for {t}")

    # Convert to list of dicts and adapt 'return' key to 'return' (Pydantic alias handles it)
    out = []
    for _, r in df.iterrows():
        out.append({
            "ticker": r["ticker"],
            "date": r["date"],
            "return": None if pd.isna(r.get("return")) else float(r.get("return")),
            "vol20": None if pd.isna(r.get("vol20")) else float(r.get("vol20")),
            "vol60": None if pd.isna(r.get("vol60")) else float(r.get("vol60")),
            "sma20": None if pd.isna(r.get("sma20")) else float(r.get("sma20")),
            "sma50": None if pd.isna(r.get("sma50")) else float(r.get("sma50")),
            "sharpe20": None if pd.isna(r.get("sharpe20")) else float(r.get("sharpe20")),
            "sharpe60": None if pd.isna(r.get("sharpe60")) else float(r.get("sharpe60")),
        })
    return out


@app.get("/summary", response_model=SummaryOut)
def get_summary():
    """
    Return an aggregated summary of the database (counts and earliest/latest dates).
    """
    try:
        df = fetch_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if df.empty:
        raise HTTPException(status_code=404, detail="No summary available")

    row = df.iloc[0].to_dict()
    return {
        "total_tickers": int(row.get("total_tickers", 0)),
        "price_rows": int(row.get("price_rows", 0)),
        "metrics_rows": int(row.get("metrics_rows", 0)),
        "earliest_price_date": row.get("earliest_price_date"),
        "latest_price_date": row.get("latest_price_date"),
        "earliest_metric_date": row.get("earliest_metric_date"),
        "latest_metric_date": row.get("latest_metric_date"),
    }
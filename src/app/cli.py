"""
Command-line utilities for FinSight.

Provides:
- `refresh` subcommand to pull data for all tracked tickers, compute metrics, and upsert into the DB.
- `metrics --ticker TICKER` subcommand to print a one-line summary for a ticker
  (latest close, return, sharpe20).

This module uses the application's db and analytics helpers and yfinance for data.
"""
import argparse
import sys
from typing import List, Dict, Any, Optional

import pandas as pd
import yfinance as yf

from app.services.analytics import compute_metrics_for_prices
from app.db import (
    create_schema,
    upsert_prices,
    upsert_metrics,
    fetch_latest_metrics,
    fetch_summary,
    _get_conn,
)


def _normalize_ticker(t: str) -> str:
    return t.strip().upper()


def _download_prices_for_ticker(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Download daily OHLCV for `ticker` and return DataFrame with columns:
    ['date','open','high','low','close','volume'] where 'date' is ISO yyyy-mm-dd.
    Raises RuntimeError if no data returned.
    """
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        raise RuntimeError(f"No price data for {ticker}")
    # Ensure expected columns
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            raise RuntimeError(f"Unexpected data format from yfinance for {ticker}")
    df = df.reset_index().rename(
        columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
    return df


def _get_tracked_tickers() -> List[str]:
    """
    Return list of tracked tickers inferred from prices and metrics tables.
    """
    sql = "SELECT DISTINCT ticker FROM prices UNION SELECT DISTINCT ticker FROM metrics ORDER BY 1;"
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
    return [r[0] for r in rows]


def cmd_refresh(args: argparse.Namespace) -> int:
    """
    Refresh command: for each tracked ticker download prices, upsert prices,
    compute metrics and upsert metrics. Prints a brief summary at the end.
    """
    period = args.period
    tickers = _get_tracked_tickers()
    if not tickers:
        print("No tickers tracked in database. Nothing to refresh.")
        return 0

    results = {"processed": 0, "errors": []}
    for ticker in tickers:
        try:
            t = _normalize_ticker(ticker)
            prices_df = _download_prices_for_ticker(t, period=period)
            # attach ticker and upsert prices
            price_rows = prices_df.assign(ticker=t).to_dict(orient="records")
            upsert_prices(price_rows)

            # compute metrics and upsert
            metrics_df = compute_metrics_for_prices(prices_df[["date", "close"]])
            if not metrics_df.empty:
                metrics_rows = []
                for _, row in metrics_df.iterrows():
                    date_val = row["date"].strftime("%Y-%m-%d") if not isinstance(row["date"], str) else row["date"]
                    metrics_rows.append(
                        {
                            "ticker": t,
                            "date": date_val,
                            "return": None if pd.isna(row["return"]) else float(row["return"]),
                            "vol20": None if pd.isna(row["vol20"]) else float(row["vol20"]),
                            "vol60": None if pd.isna(row["vol60"]) else float(row["vol60"]),
                            "sma20": None if pd.isna(row["sma20"]) else float(row["sma20"]),
                            "sma50": None if pd.isna(row["sma50"]) else float(row["sma50"]),
                            "sharpe20": None if pd.isna(row["sharpe20"]) else float(row["sharpe20"]),
                            "sharpe60": None if pd.isna(row["sharpe60"]) else float(row["sharpe60"]),
                        }
                    )
                upsert_metrics(metrics_rows)
            results["processed"] += 1
            print(f"Refreshed {t}")
        except Exception as exc:
            results["errors"].append({"ticker": ticker, "error": str(exc)})
            print(f"Error refreshing {ticker}: {exc}")

    # final summary
    try:
        summary = fetch_summary().to_dict(orient="records")[0]
    except Exception:
        summary = {}
    print("\nRefresh complete.")
    print(f"Processed: {results['processed']}, Errors: {len(results['errors'])}")
    if results["errors"]:
        print("Errors:")
        for err in results["errors"]:
            print(f" - {err['ticker']}: {err['error']}")
    if summary:
        print("\nDB Summary:")
        for k, v in summary.items():
            print(f"  {k}: {v}")
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    """
    Metrics command: prints a one-line summary for the provided ticker.
    Output: TICKER | close: XXX | return: YYY | sharpe20: ZZZ
    """
    if not args.ticker:
        print("Please provide --ticker TICKER")
        return 2
    t = _normalize_ticker(args.ticker)

    # fetch latest metrics for all tickers and filter
    try:
        metrics_df = fetch_latest_metrics()
    except Exception as exc:
        print(f"Failed to fetch metrics: {exc}")
        return 1

    row = metrics_df[metrics_df["ticker"].str.upper() == t]
    if row.empty:
        print(f"No metrics found for {t}")
        return 1

    m = row.iloc[0].to_dict()

    # fetch latest close from prices table
    close = None
    with _get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT close, date FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 1", (t,))
        r = cur.fetchone()
        if r:
            close = r[0]
            close_date = r[1]
        else:
            close_date = None

    # prepare values for printing
    ret = None if pd.isna(m.get("return")) else float(m.get("return"))
    sharpe20 = None if pd.isna(m.get("sharpe20")) else float(m.get("sharpe20"))

    print(f"{t} | close: {'' if close is None else round(float(close),4)} (as of {close_date}) | return: {'' if ret is None else round(ret,6)} | sharpe20: {'' if sharpe20 is None else round(sharpe20,6)}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    Entrypoint for the CLI. Supports subcommands `refresh` and `metrics`.
    """
    parser = argparse.ArgumentParser(prog="finsight", description="FinSight CLI")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # refresh
    p_refresh = subparsers.add_parser("refresh", help="Refresh data and recompute metrics for tracked tickers")
    p_refresh.add_argument("--period", "-p", default="2y", help="yfinance period (e.g., 1y, 2y, max)")
    p_refresh.set_defaults(func=cmd_refresh)

    # metrics
    p_metrics = subparsers.add_parser("metrics", help="Show one-line metrics summary for a ticker")
    p_metrics.add_argument("--ticker", "-t", required=True, help="Ticker symbol (e.g., AAPL)")
    p_metrics.set_defaults(func=cmd_metrics)

    args = parser.parse_args(argv)

    # ensure DB schema exists
    try:
        create_schema()
    except Exception as exc:
        print(f"Failed to initialize DB schema: {exc}")
        return 1

    # dispatch
    try:
        return args.func(args)
    except Exception as exc:
        print(f"Unhandled error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
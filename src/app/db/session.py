"""
SQLite helpers for FinSight.

Provides schema creation and simple upsert/fetch helpers for prices and metrics.
All functions use context managers to ensure connections are safely closed.
"""
from typing import Iterable, Mapping, Optional
import sqlite3
import pandas as pd


def _get_conn(db_path: str = "finsight.db") -> sqlite3.Connection:
    """
    Create a sqlite3 connection with sensible defaults.

    Parameters
    - db_path: path to the sqlite database file

    Returns
    - sqlite3.Connection (caller should not close when using `with _get_conn(...) as conn`)
    """
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    # enforce foreign keys if later needed
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(db_path: str = "finsight.db") -> None:
    """
    Create the prices and metrics tables if they do not exist.

    Tables:
    - prices(id INTEGER PRIMARY KEY, ticker TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume INTEGER)
      with UNIQUE(ticker, date) to avoid duplicate rows.

    - metrics(id INTEGER PRIMARY KEY, ticker TEXT, date TEXT, return REAL, vol20 REAL, vol60 REAL,
      sma20 REAL, sma50 REAL, sharpe20 REAL, sharpe60 REAL) with UNIQUE(ticker, date).

    Parameters
    - db_path: path to the sqlite database file
    """
    with _get_conn(db_path) as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                UNIQUE(ticker, date)
            );

            CREATE INDEX IF NOT EXISTS idx_prices_ticker_date ON prices(ticker, date);

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY,
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                return REAL,
                vol20 REAL,
                vol60 REAL,
                sma20 REAL,
                sma50 REAL,
                sharpe20 REAL,
                sharpe60 REAL,
                UNIQUE(ticker, date)
            );

            CREATE INDEX IF NOT EXISTS idx_metrics_ticker_date ON metrics(ticker, date);
            """
        )
        conn.commit()


def upsert_prices(df_or_rows: Iterable[Mapping], db_path: str = "finsight.db") -> None:
    """
    Upsert price rows into the prices table.

    Parameters
    - df_or_rows: Iterable of mappings (e.g., a pandas.DataFrame.to_dict(orient='records'))
      Each record must contain keys: ticker, date, open, high, low, close, volume
    - db_path: path to the sqlite database file

    Notes:
    - Uses SQLite ON CONFLICT DO UPDATE to replace values for (ticker, date).
    - Date is stored as text; caller should ensure consistent formatting (ISO8601 recommended).
    """
    sql = """
    INSERT INTO prices (ticker, date, open, high, low, close, volume)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, date) DO UPDATE SET
      open=excluded.open,
      high=excluded.high,
      low=excluded.low,
      close=excluded.close,
      volume=excluded.volume;
    """
    # normalize input to list of tuples
    rows = []
    for r in df_or_rows:
        rows.append((
            r.get("ticker"),
            r.get("date"),
            r.get("open"),
            r.get("high"),
            r.get("low"),
            r.get("close"),
            r.get("volume"),
        ))

    if not rows:
        return

    with _get_conn(db_path) as conn:
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()


def upsert_metrics(df_or_rows: Iterable[Mapping], db_path: str = "finsight.db") -> None:
    """
    Upsert metric rows into the metrics table.

    Parameters
    - df_or_rows: Iterable of mappings (e.g., DataFrame.to_dict(orient='records'))
      Each record must contain keys: ticker, date, return, vol20, vol60, sma20, sma50, sharpe20, sharpe60
    - db_path: path to the sqlite database file

    Notes:
    - Uses SQLite ON CONFLICT DO UPDATE to replace values for (ticker, date).
    """
    sql = """
    INSERT INTO metrics (ticker, date, return, vol20, vol60, sma20, sma50, sharpe20, sharpe60)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ticker, date) DO UPDATE SET
      return=excluded.return,
      vol20=excluded.vol20,
      vol60=excluded.vol60,
      sma20=excluded.sma20,
      sma50=excluded.sma50,
      sharpe20=excluded.sharpe20,
      sharpe60=excluded.sharpe60;
    """
    rows = []
    for r in df_or_rows:
        rows.append((
            r.get("ticker"),
            r.get("date"),
            r.get("return"),
            r.get("vol20"),
            r.get("vol60"),
            r.get("sma20"),
            r.get("sma50"),
            r.get("sharpe20"),
            r.get("sharpe60"),
        ))

    if not rows:
        return

    with _get_conn(db_path) as conn:
        cur = conn.cursor()
        cur.executemany(sql, rows)
        conn.commit()


def fetch_latest_metrics(db_path: str = "finsight.db") -> pd.DataFrame:
    """
    Fetch the latest metric row for each ticker.

    Parameters
    - db_path: path to the sqlite database file

    Returns
    - pandas.DataFrame containing the latest metrics per ticker (columns as in metrics table).
    """
    sql = """
    SELECT m.ticker, m.date, m.return, m.vol20, m.vol60, m.sma20, m.sma50, m.sharpe20, m.sharpe60
    FROM metrics m
    JOIN (
        SELECT ticker, MAX(date) AS max_date
        FROM metrics
        GROUP BY ticker
    ) latest
      ON m.ticker = latest.ticker AND m.date = latest.max_date
    ORDER BY m.ticker;
    """
    with _get_conn(db_path) as conn:
        df = pd.read_sql_query(sql, conn)
    return df


def fetch_summary(db_path: str = "finsight.db") -> pd.DataFrame:
    """
    Produce a small summary of the database contents.

    Summary includes:
    - total_tickers: number of distinct tickers in prices table
    - price_rows: total number of price rows
    - metrics_rows: total number of metric rows
    - earliest_price_date, latest_price_date (ISO strings or NULL)
    - earliest_metric_date, latest_metric_date (ISO strings or NULL)

    Parameters
    - db_path: path to the sqlite database file

    Returns
    - pandas.DataFrame with a single row summarizing the DB.
    """
    summary_sql = """
    SELECT
      (SELECT COUNT(DISTINCT ticker) FROM prices) AS total_tickers,
      (SELECT COUNT(*) FROM prices) AS price_rows,
      (SELECT COUNT(*) FROM metrics) AS metrics_rows,
      (SELECT MIN(date) FROM prices) AS earliest_price_date,
      (SELECT MAX(date) FROM prices) AS latest_price_date,
      (SELECT MIN(date) FROM metrics) AS earliest_metric_date,
      (SELECT MAX(date) FROM metrics) AS latest_metric_date
    ;
    """
    with _get_conn(db_path) as conn:
        df = pd.read_sql_query(summary_sql, conn)
    return df
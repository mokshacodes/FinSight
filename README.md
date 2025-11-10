# FinSight

FinSight is a compact FastAPI backend for financial data analytics. It ingests OHLCV price series (via yfinance), computes time-series metrics, stores prices and metrics in SQLite, and exposes endpoints and a small CLI for managing tickers and retrieving analytics.

## What it does
- Tracks stock tickers and stores historical daily prices.
- Computes per-ticker metrics (returns, rolling volatilities, simple moving averages, rolling Sharpe ratios) using pandas.
- Persists prices and metrics in a local SQLite database.
- Provides HTTP endpoints and a CLI to add tickers, refresh data, and retrieve metrics and summaries.

## Quick start (macOS / Linux)
1. Clone and enter the project:
   ```
   git clone <repo-url> FinSight
   cd FinSight
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Initialize the DB (app startup also creates schema) and run the API:
   ```
   uvicorn app.main:app --reload
   ```
   The API is available at http://127.0.0.1:8000

## Example API requests
- List tracked tickers:
  ```
  curl http://127.0.0.1:8000/tickers
  ```

- Add a ticker (POST JSON):
  ```
  curl -X POST http://127.0.0.1:8000/add_ticker -H "Content-Type: application/json" -d '{"ticker":"AAPL"}'
  ```

- Refresh all tracked tickers (re-download prices, recompute metrics):
  ```
  curl -X POST "http://127.0.0.1:8000/refresh"
  ```

- Get latest metrics for a ticker:
  ```
  curl "http://127.0.0.1:8000/metrics?ticker=AAPL"
  ```

- Get DB summary:
  ```
  curl http://127.0.0.1:8000/summary
  ```

## CLI
- Refresh tracked tickers:
  ```
  python -m app.cli refresh
  ```

- Print one-line metrics for a ticker:
  ```
  python -m app.cli metrics --ticker AAPL
  ```

## Metrics — formulas & notes
All rolling calculations are computed with pandas rolling(..., closed='left') so that each metric at time t uses only historical data strictly before t (prevents look-ahead bias).

- return: simple period-over-period return: return_t = (close_t / close_{t-1}) - 1
- vol20 / vol60: rolling standard deviation of returns over the prior 20 / 60 periods (unannualized)
- sma20 / sma50: simple moving average of close over the prior 20 / 50 periods
- sharpe20 / sharpe60: rolling mean(return) / rolling std(return) over the prior 20 / 60 periods
- Rows with insufficient history for a particular metric are skipped so stored metrics only contain values computed from full historical windows.

## Testing
Unit tests use pytest:
```
pytest tests/unit
```
The repository includes tests for the analytics module that use a synthetic closing-price series to assert rolling metrics and row counts.

## What to build next
- Add authentication and rate-limiting for the API.
- Support configurable periodicity (intraday / weekly) and automated scheduling (cron or APScheduler).
- Add more metrics (drawdown, rolling beta vs benchmark).
- Expose time-series endpoints for charting (e.g., /prices?ticker=AAPL&period=1y).
- Add Dockerfile and CI (GitHub Actions) to run tests and linting automatically.

License: MIT (add LICENSE file as needed).
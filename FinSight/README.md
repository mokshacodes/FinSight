# FinSight

FinSight is a FastAPI application designed for financial data analysis and visualization. It provides endpoints for managing financial tickers, performing analytics, and retrieving metrics.

## Project Structure

```
FinSight
├── src
│   └── app
│       ├── __init__.py
│       ├── main.py
│       ├── api
│       │   ├── __init__.py
│       │   └── v1
│       │       ├── __init__.py
│       │       ├── routes.py
│       │       └── analytics.py
│       ├── core
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── logging.py
│       ├── db
│       │   ├── __init__.py
│       │   ├── session.py
│       │   └── schema.sql
│       ├── models
│       │   ├── __init__.py
│       │   └── models.py
│       ├── schemas
│       │   ├── __init__.py
│       │   └── schemas.py
│       └── services
│           ├── __init__.py
│           └── analytics.py
├── tests
│   ├── unit
│   │   ├── test_models.py
│   │   ├── test_routes.py
│   │   └── test_analytics.py
│   └── integration
│       └── test_api.py
├── migrations
│   ├── env.py
│   └── versions
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/FinSight.git
   cd FinSight
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the FastAPI application, use the following command:
```
uvicorn src.app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

## API Endpoints

- `GET /tickers`: Retrieve a list of financial tickers.
- `POST /add_ticker`: Add a new financial ticker.
- `POST /refresh`: Refresh the data for existing tickers.
- `GET /metrics`: Retrieve analytics metrics.
- `GET /summary`: Get a summary of the financial data.

## Testing

To run the unit tests, use:
```
pytest tests/unit
```

For integration tests, run:
```
pytest tests/integration
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
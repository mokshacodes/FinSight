from fastapi.testclient import TestClient
from src.app.main import app

client = TestClient(app)

def test_get_tickers():
    response = client.get("/tickers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_add_ticker():
    response = client.post("/add_ticker", json={"ticker": "AAPL"})
    assert response.status_code == 201
    assert response.json() == {"message": "Ticker added successfully"}

def test_refresh():
    response = client.post("/refresh")
    assert response.status_code == 200
    assert response.json() == {"message": "Data refreshed successfully"}

def test_get_metrics():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "metrics" in response.json()

def test_get_summary():
    response = client.get("/summary")
    assert response.status_code == 200
    assert "summary" in response.json()
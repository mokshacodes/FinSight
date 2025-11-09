from fastapi import HTTPException
from app.services.analytics import calculate_metrics
import pytest

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
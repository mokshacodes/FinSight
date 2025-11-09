from pydantic import BaseModel
from typing import List, Optional

class Ticker(BaseModel):
    symbol: str
    name: str
    price: float
    volume: int

class TickerCreate(BaseModel):
    symbol: str
    name: str

class TickerResponse(BaseModel):
    ticker: Ticker

class TickerListResponse(BaseModel):
    tickers: List[Ticker]

class MetricsResponse(BaseModel):
    average_price: float
    total_volume: int

class SummaryResponse(BaseModel):
    total_tickers: int
    average_price: float
    total_volume: int
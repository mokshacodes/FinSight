from fastapi import APIRouter
from app.schemas.schemas import TickerCreate, TickerResponse
from app.services.analytics import add_ticker, refresh_tickers, get_metrics, get_summary

router = APIRouter()

@router.get("/tickers", response_model=list[TickerResponse])
async def read_tickers():
    return await get_metrics()

@router.post("/add_ticker", response_model=TickerResponse)
async def create_ticker(ticker: TickerCreate):
    return await add_ticker(ticker)

@router.post("/refresh")
async def refresh():
    await refresh_tickers()
    return {"message": "Tickers refreshed successfully"}

@router.get("/metrics")
async def metrics():
    return await get_metrics()

@router.get("/summary")
async def summary():
    return await get_summary()
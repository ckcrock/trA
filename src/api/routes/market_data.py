"""
Market data API routes — LTP, quotes, historical data.
Reference: SYSTEM_ARCHITECTURE.md §3.2
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, Dict
from datetime import datetime
from src.api.dependencies import get_data_client, get_symbol_resolver

router = APIRouter()


@router.get("/ltp")
async def get_ltp(
    symbol: str = Query(..., description="Trading symbol, e.g., SBIN-EQ"),
    exchange: str = Query("NSE", description="Exchange: NSE, BSE, NFO"),
    data_client=Depends(get_data_client),
    resolver=Depends(get_symbol_resolver),
):
    """Get Last Traded Price for a symbol."""
    instrument = resolver.resolve_by_symbol(symbol, exchange)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")

    ltp = await data_client.get_ltp(
        exchange=exchange,
        trading_symbol=instrument["symbol"],
        symbol_token=instrument["token"],
    )
    return {"symbol": symbol, "exchange": exchange, "ltp": ltp}


@router.get("/quote")
async def get_quote(
    symbol: str = Query(..., description="Trading symbol"),
    exchange: str = Query("NSE"),
    data_client=Depends(get_data_client),
    resolver=Depends(get_symbol_resolver),
):
    """Get full market quote for a symbol."""
    instrument = resolver.resolve_by_symbol(symbol, exchange)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")

    quote = await data_client.get_quote(
        exchange=exchange,
        symbol_token=instrument["token"],
    )
    return {"symbol": symbol, "exchange": exchange, "quote": quote}


@router.get("/history")
async def get_history(
    symbol: str = Query(..., description="Trading symbol"),
    exchange: str = Query("NSE"),
    interval: str = Query("ONE_DAY", description="Candle interval"),
    from_date: str = Query(..., description="Start date YYYY-MM-DD HH:MM"),
    to_date: str = Query(..., description="End date YYYY-MM-DD HH:MM"),
    data_client=Depends(get_data_client),
    resolver=Depends(get_symbol_resolver),
):
    """Get historical candle data."""
    instrument = resolver.resolve_by_symbol(symbol, exchange)
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Symbol not found: {symbol}")

    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d %H:%M")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date format must be YYYY-MM-DD HH:MM")

    df = await data_client.get_historical_data(
        symbol_token=instrument["token"],
        exchange=exchange,
        interval=interval,
        from_date=from_dt,
        to_date=to_dt,
    )

    if df is None or df.empty:
        return {"symbol": symbol, "data": [], "count": 0}

    records = df.to_dict(orient="records")
    # Convert timestamps to strings
    for r in records:
        if "timestamp" in r:
            r["timestamp"] = str(r["timestamp"])

    return {"symbol": symbol, "exchange": exchange, "interval": interval, "data": records, "count": len(records)}

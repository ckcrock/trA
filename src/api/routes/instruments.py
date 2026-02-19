from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict
from src.api.dependencies import get_symbol_resolver
from src.catalog.symbol_resolver import SymbolResolver

router = APIRouter()

@router.get("/resolve", response_model=Optional[Dict])
async def resolve_instrument(
    symbol: str = Query(..., description="Symbol to resolve, e.g., SBIN-EQ"),
    exchange: str = "NSE",
    resolver: SymbolResolver = Depends(get_symbol_resolver)
):
    return resolver.resolve_by_symbol(symbol, exchange)

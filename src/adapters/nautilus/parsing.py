"""
Data parsing and translation utilities for Angel One Nautilus Adapter.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import pandas as pd



try:
    from nautilus_trader.model.data import Bar, QuoteTick, TradeTick, BarType
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.enums import BarAggregation, PriceType, OrderSide, OrderType, TimeInForce, OrderStatus
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes
    class Bar: pass
    class QuoteTick: pass
    class TradeTick: pass
    class BarType: pass
    class InstrumentId: pass
    class BarAggregation: pass
    class PriceType: pass
    class OrderSide: pass
    class OrderType: pass
    class TimeInForce: pass
    class OrderStatus: pass
    class Price: pass
    class Quantity: pass
    def dt_to_unix_nanos(dt): return 0

# Import local constants
from .constants import (
    ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, ORDER_TYPE_SL_M, ORDER_TYPE_SL_L,
    PRODUCT_MIS, PRODUCT_CNC, PRODUCT_NRML, PRODUCT_BO
)


def parse_bar(bar_type: BarType, candle: list, instrument: Any, ts_init: int) -> Optional[Bar]:
    """
    Parse Angel One historical candle into Nautilus Bar.
    Angel Candle: [timestamp, open, high, low, close, volume]
    """
    if not NAUTILUS_AVAILABLE:
        return None

    try:
        # Timestamp is usually ISO string or datetime object from data_client
        ts_str = candle[0]
        if isinstance(ts_str, str):
            dt = pd.to_datetime(ts_str).to_pydatetime()
        elif isinstance(ts_str, datetime):
            dt = ts_str
        else:
            return None
            
        ts_event = dt_to_unix_nanos(dt)
        
        # FIX: ts_init cannot be 0 in BacktestEngine (causes dict not callable error)
        if ts_init == 0:
            ts_init = ts_event

        return Bar(
            bar_type=bar_type,
            open=instrument.make_price(candle[1]),
            high=instrument.make_price(candle[2]),
            low=instrument.make_price(candle[3]),
            close=instrument.make_price(candle[4]),
            volume=instrument.make_qty(candle[5]),
            ts_event=ts_event,
            ts_init=ts_init
        )
    except Exception as e:
        logger.error(f"Error parsing candle: {e}")
        return None


def parse_quote_tick(data: dict, instrument_provider: Any, ts_init: int) -> Optional[QuoteTick]:
    """
    Parse Angel One WebSocket tick into Nautilus QuoteTick.
    """
    if not NAUTILUS_AVAILABLE:
        return None
        
    try:
        # Resolve instrument using token
        token = data.get('token')
        if not token:
            return None
            
        # In a real implementation, we'd need a fast token->instrument lookup
        # For now, we assume the instrument_provider has a helper or we passed the instrument ID
        # This is a simplification; optimal path requires token map
        # ...
        
        # Placeholder for tick parsing logic
        # Angel tick keys: 'bs' (best sell?), 'bp' (best buy?) - need to check WS docs
        # Assuming standard keys for now based on typical WS output
        
        # If data is Best 5, we might extract top level
        # If data is LTP/Quote, we might not have bid/ask size
        
        return None  # TODO: Implement full tick parsing
    except Exception as e:
        logger.error(f"Error parsing quote tick: {e}")
        return None


# Order Translation

def translate_order_type_to_angel(order_type: OrderType) -> str:
    if not NAUTILUS_AVAILABLE: return "MARKET"
    
    if order_type == OrderType.MARKET:
        return ORDER_TYPE_MARKET
    elif order_type == OrderType.LIMIT:
        return ORDER_TYPE_LIMIT
    elif order_type == OrderType.STOP_MARKET:
        return ORDER_TYPE_SL_M
    elif order_type == OrderType.STOP_LIMIT:
        return ORDER_TYPE_SL_L
    return ORDER_TYPE_MARKET

def translate_time_in_force_to_angel(tif: TimeInForce) -> str:
    if not NAUTILUS_AVAILABLE: return "INTRADAY"
    
    if tif == TimeInForce.IOC:
        return "IOC"
    # Mapping Day to Intraday/Delivery depends on product type really,
    # but here we might default to Intraday for Day TIF if not specified
    return "DAY"  # Angel specific duration

def translate_order_status_from_angel(status: str) -> OrderStatus:
    if not NAUTILUS_AVAILABLE: return None
    
    s = status.lower()
    if s == "complete":
        return OrderStatus.FILLED
    elif s == "rejected":
        return OrderStatus.REJECTED
    elif s == "cancelled":
        return OrderStatus.CANCELED
    elif s == "open" or s == "trigger pending":
        return OrderStatus.ACCEPTED
    elif s == "validation pending":
        return OrderStatus.SUBMITTED
    return OrderStatus.SUBMITTED

"""
Data parsing and translation utilities for Angel One Nautilus Adapter.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)

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

        if hasattr(instrument, "make_price") and hasattr(instrument, "make_qty"):
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

        # Fallback for lightweight instrument references.
        return Bar(
            bar_type=bar_type,
            open=Price.from_str(str(float(candle[1]))),
            high=Price.from_str(str(float(candle[2]))),
            low=Price.from_str(str(float(candle[3]))),
            close=Price.from_str(str(float(candle[4]))),
            volume=Quantity.from_int(int(float(candle[5] or 0))),
            ts_event=ts_event,
            ts_init=ts_init,
        )
    except Exception as e:
        logger.error(f"Error parsing candle: {e}")
        return None


def _price_from_angel(raw: Any, assume_paise: bool = True) -> float:
    """Convert Angel price fields to float rupee price."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0

    if assume_paise and value != 0:
        # Angel WS commonly provides paise integers (e.g., 50025 => 500.25).
        if abs(value) >= 1000 and float(int(value)) == value:
            return value / 100.0
    return value


def _qty_from_angel(raw: Any) -> int:
    try:
        return int(float(raw or 0))
    except (TypeError, ValueError):
        return 0


def _timestamp_ns_from_angel(data: dict) -> int:
    """Extract event timestamp in nanos from Angel tick payload."""
    raw = (
        data.get("exchange_timestamp")
        or data.get("last_traded_timestamp")
        or data.get("timestamp")
    )
    if raw is None:
        return 0

    try:
        # Numeric timestamp (ms/us/ns)
        ts = int(float(raw))
        if ts > 10**16:      # already ns
            return ts
        if ts > 10**13:      # us -> ns
            return ts * 1000
        if ts > 10**10:      # ms -> ns
            return ts * 1_000_000
        return ts * 1_000_000_000  # seconds -> ns
    except (TypeError, ValueError):
        pass

    try:
        dt = pd.to_datetime(raw).to_pydatetime()
        return dt_to_unix_nanos(dt)
    except Exception:
        return 0


def parse_quote_tick(data: dict, instrument_provider: Any, ts_init: int) -> Optional[QuoteTick]:
    """
    Parse Angel One WebSocket tick into Nautilus QuoteTick.
    """
    if not NAUTILUS_AVAILABLE:
        return None
        
    try:
        # Resolve instrument using token
        token = data.get("token") or data.get("symbol_token")
        if not token:
            return None

        instrument_ref = None
        if hasattr(instrument_provider, "find_by_token"):
            instrument_ref = instrument_provider.find_by_token(str(token))
        if instrument_ref is None:
            return None

        raw_instrument_id = getattr(instrument_ref, "instrument_id", None)
        if raw_instrument_id is None:
            return None
        if isinstance(raw_instrument_id, InstrumentId):
            instrument_id = raw_instrument_id
        else:
            instrument_id = InstrumentId.from_str(str(raw_instrument_id))

        best_buy = data.get("best_5_buy_data") or []
        best_sell = data.get("best_5_sell_data") or []
        best_buy0 = best_buy[0] if isinstance(best_buy, list) and best_buy else {}
        best_sell0 = best_sell[0] if isinstance(best_sell, list) and best_sell else {}

        ltp = _price_from_angel(
            data.get("last_traded_price")
            or data.get("ltp")
            or data.get("last_price")
            or data.get("close"),
            assume_paise=True,
        )
        bid = _price_from_angel(
            data.get("best_bid_price")
            or data.get("bid")
            or best_buy0.get("price")
            or ltp,
            assume_paise=True,
        )
        ask = _price_from_angel(
            data.get("best_ask_price")
            or data.get("ask")
            or best_sell0.get("price")
            or ltp,
            assume_paise=True,
        )
        bid_qty = _qty_from_angel(
            data.get("best_bid_qty")
            or data.get("bid_qty")
            or best_buy0.get("quantity")
            or best_buy0.get("qty")
            or 0
        )
        ask_qty = _qty_from_angel(
            data.get("best_ask_qty")
            or data.get("ask_qty")
            or best_sell0.get("quantity")
            or best_sell0.get("qty")
            or 0
        )

        ts_event = _timestamp_ns_from_angel(data)
        if ts_event == 0:
            ts_event = ts_init
        if ts_init == 0:
            ts_init = ts_event

        return QuoteTick(
            instrument_id=instrument_id,
            bid_price=Price.from_str(str(bid)),
            ask_price=Price.from_str(str(ask)),
            bid_size=Quantity.from_int(max(0, bid_qty)),
            ask_size=Quantity.from_int(max(0, ask_qty)),
            ts_event=ts_event,
            ts_init=ts_init,
        )
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

"""
Constants and Enums for Angel One Nautilus Adapter.
"""

try:
    from nautilus_trader.model.enums import (
        OrderType, OrderSide, TimeInForce, OrderStatus, 
        PositionSide, AggregationSource, PriceType
    )
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Define dummy classes if Nautilus is missing to avoid import errors
    class OrderType: pass
    class OrderSide: pass
    class TimeInForce: pass
    class OrderStatus: pass
    class PositionSide: pass
    class AggregationSource: pass
    class PriceType: pass

# Venue identifier
ANGEL_VENUE = "ANGELONE"

# Rate Limits (per second)
RATE_LIMIT_DATA = 3
RATE_LIMIT_EXECUTION = 3

# Product Types
PRODUCT_MIS = "INTRADAY"
PRODUCT_CNC = "DELIVERY"
PRODUCT_NRML = "CARRYFORWARD"
PRODUCT_BO = "BO"

# Order Types
ORDER_TYPE_MARKET = "MARKET"
ORDER_TYPE_LIMIT = "LIMIT"
ORDER_TYPE_SL_M = "STOPLOSS_MARKET"
ORDER_TYPE_SL_L = "STOPLOSS_LIMIT"

# Exchange Segment mapping
EXCHANGE_NSE = "NSE"
EXCHANGE_NFO = "NFO"
EXCHANGE_BSE = "BSE"
EXCHANGE_BFO = "BFO"
EXCHANGE_MCX = "MCX"
EXCHANGE_CDS = "CDS"

# WebSocket Modes
WS_MODE_LTP = 1
WS_MODE_QUOTE = 2
WS_MODE_SNAP_QUOTE = 3

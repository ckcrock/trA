"""
System-wide constants for the trading platform.
Reference: SYSTEM_ARCHITECTURE.md, TRADING_REFERENCE_COMPLETE.md
"""


# ─── Exchange Codes ───────────────────────────────────────────────────
class Exchange:
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"       # NSE F&O
    BFO = "BFO"       # BSE F&O
    MCX = "MCX"       # Commodity
    CDS = "CDS"       # Currency
    INDICES = "INDICES"


# ─── Product Types ────────────────────────────────────────────────────
class ProductType:
    INTRADAY = "INTRADAY"       # MIS — auto square-off
    DELIVERY = "DELIVERY"       # CNC — delivery
    CARRYFORWARD = "CARRYFORWARD"  # NRML — F&O carry forward
    MARGIN = "MARGIN"           # Margin trading
    BO = "BO"                   # Bracket Order
    CO = "CO"                   # Cover Order


# ─── Order Types ──────────────────────────────────────────────────────
class OrderType:
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "STOPLOSS_LIMIT"
    STOPLOSS_MARKET = "STOPLOSS_MARKET"


# ─── Transaction Types ───────────────────────────────────────────────
class TransactionType:
    BUY = "BUY"
    SELL = "SELL"


# ─── Order Variety ────────────────────────────────────────────────────
class Variety:
    NORMAL = "NORMAL"
    STOPLOSS = "STOPLOSS"
    AMO = "AMO"             # After Market Order
    ROBO = "ROBO"           # Bracket Order


# ─── Order Duration ──────────────────────────────────────────────────
class Duration:
    DAY = "DAY"
    IOC = "IOC"             # Immediate or Cancel


# ─── Order Status ────────────────────────────────────────────────────
class OrderStatus:
    PENDING = "pending"
    OPEN = "open"
    COMPLETE = "complete"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    TRIGGER_PENDING = "trigger pending"


# ─── Market Data Modes (WebSocket) ───────────────────────────────────
class DataMode:
    LTP = 1
    QUOTE = 2
    SNAP_QUOTE = 3


# ─── Market Hours (IST) ─────────────────────────────────────────────
class MarketHours:
    PRE_OPEN_START = "09:00"
    PRE_OPEN_END = "09:15"
    MARKET_OPEN = "09:15"
    MARKET_CLOSE = "15:30"
    POST_MARKET_START = "15:30"
    POST_MARKET_END = "16:00"
    MIS_SQUARE_OFF = "15:15"     # Broker auto square-off for MIS


# ─── Historical Data Intervals ───────────────────────────────────────
class Interval:
    ONE_MINUTE = "ONE_MINUTE"
    THREE_MINUTE = "THREE_MINUTE"
    FIVE_MINUTE = "FIVE_MINUTE"
    TEN_MINUTE = "TEN_MINUTE"
    FIFTEEN_MINUTE = "FIFTEEN_MINUTE"
    THIRTY_MINUTE = "THIRTY_MINUTE"
    ONE_HOUR = "ONE_HOUR"
    ONE_DAY = "ONE_DAY"


# ─── Common Symbol Tokens (Angel One) ────────────────────────────────
# Reference: TRADING_REFERENCE_COMPLETE.md
COMMON_TOKENS = {
    "NIFTY_50": "99926000",
    "NIFTY_BANK": "99926009",
    "NIFTY_FIN": "99926037",
    "NIFTY_IT": "99926013",
    "SENSEX": "99919000",
    "SBIN": "3045",
    "RELIANCE": "2885",
    "TCS": "11536",
    "INFY": "1594",
    "HDFCBANK": "1333",
    "ICICIBANK": "4963",
    "KOTAKBANK": "1922",
    "HINDUNILVR": "1394",
    "ITC": "1660",
    "LT": "11483",
    "AXISBANK": "5900",
    "BAJFINANCE": "317",
    "MARUTI": "10999",
    "TATAMOTORS": "3456",
    "TATASTEEL": "3499",
    "WIPRO": "3787",
    "HCLTECH": "7229",
    "SUNPHARMA": "3351",
    "ADANIENT": "25",
    "BHARTIARTL": "10604",
}


# ─── Indian Market Tax Rates ─────────────────────────────────────────
class TaxRates:
    STT_DELIVERY_BUY = 0.001       # 0.1% on buy
    STT_DELIVERY_SELL = 0.001      # 0.1% on sell
    STT_INTRADAY_SELL = 0.00025    # 0.025% on sell only
    STT_FNO_SELL = 0.000125        # 0.0125% on sell
    GST = 0.18                     # 18% on brokerage + transaction
    SEBI_CHARGES = 0.000001        # ₹10 per crore
    STAMP_DUTY_BUY = 0.00015       # 0.015% on buy (varies by state)
    STCG_RATE = 0.15               # 15% Short-term capital gains
    LTCG_RATE = 0.10               # 10% Long-term (>1yr, >₹1L exemption)


# ─── Performance ─────────────────────────────────────────────────────
RISK_FREE_RATE_INDIA = 0.065       # ~6.5% (10-yr govt bond yield)
TRADING_DAYS_PER_YEAR = 252

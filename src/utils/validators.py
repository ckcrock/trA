"""
Input validation utilities for orders, prices, and quantities.
Reference: SYSTEM_ARCHITECTURE.md, MISSING_REQUIREMENTS §2
"""

import logging
from typing import Dict, Optional, Tuple
from src.utils.constants import (
    Exchange, ProductType, OrderType, TransactionType,
    Variety, Duration
)

logger = logging.getLogger(__name__)

# Valid enum values for quick validation
VALID_EXCHANGES = {Exchange.NSE, Exchange.BSE, Exchange.NFO, Exchange.BFO, Exchange.MCX, Exchange.CDS}
VALID_PRODUCT_TYPES = {ProductType.INTRADAY, ProductType.DELIVERY, ProductType.CARRYFORWARD, ProductType.MARGIN}
VALID_ORDER_TYPES = {OrderType.MARKET, OrderType.LIMIT, OrderType.STOPLOSS_LIMIT, OrderType.STOPLOSS_MARKET}
VALID_TRANSACTION_TYPES = {TransactionType.BUY, TransactionType.SELL}
VALID_VARIETIES = {Variety.NORMAL, Variety.STOPLOSS, Variety.AMO, Variety.ROBO}
VALID_DURATIONS = {Duration.DAY, Duration.IOC}

# Angel One tick size (price precision)
TICK_SIZE = 0.05


def validate_order_params(params: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate order parameters before submission.
    Returns (is_valid, error_message).
    """
    # Required fields
    required = ["tradingsymbol", "symboltoken", "exchange", "transaction_type", "qty", "ordertype"]
    for field in required:
        if field not in params or not params[field]:
            return False, f"Missing required field: {field}"

    # Exchange validation
    if params.get("exchange") not in VALID_EXCHANGES:
        return False, f"Invalid exchange: {params.get('exchange')}"

    # Transaction type
    if params.get("transaction_type") not in VALID_TRANSACTION_TYPES:
        return False, f"Invalid transaction type: {params.get('transaction_type')}"

    # Order type
    if params.get("ordertype") not in VALID_ORDER_TYPES:
        return False, f"Invalid order type: {params.get('ordertype')}"

    # Quantity must be positive
    qty = params.get("qty")
    try:
        qty_int = int(qty)
        if qty_int <= 0:
            return False, f"Quantity must be positive, got: {qty}"
    except (ValueError, TypeError):
        return False, f"Invalid quantity: {qty}"

    # Price validation for LIMIT orders
    order_type = params.get("ordertype")
    if order_type in (OrderType.LIMIT, OrderType.STOPLOSS_LIMIT):
        price = params.get("price", 0)
        try:
            price_float = float(price)
            if price_float <= 0:
                return False, f"Price must be positive for {order_type}, got: {price}"
        except (ValueError, TypeError):
            return False, f"Invalid price: {price}"

    # Trigger price for SL orders
    if order_type in (OrderType.STOPLOSS_LIMIT, OrderType.STOPLOSS_MARKET):
        trigger = params.get("triggerprice", 0)
        try:
            trigger_float = float(trigger)
            if trigger_float <= 0:
                return False, f"Trigger price must be positive for {order_type}, got: {trigger}"
        except (ValueError, TypeError):
            return False, f"Invalid trigger price: {trigger}"

    return True, None


def validate_quantity_lot_size(quantity: int, lot_size: int = 1) -> Tuple[bool, Optional[str]]:
    """Validate quantity is a multiple of lot size (for F&O)."""
    if quantity <= 0:
        return False, "Quantity must be positive"
    if lot_size > 1 and quantity % lot_size != 0:
        return False, f"Quantity {quantity} must be a multiple of lot size {lot_size}"
    return True, None


def validate_price_tick(price: float, tick_size: float = TICK_SIZE) -> float:
    """Round price to nearest valid tick size."""
    if price <= 0:
        return 0.0
    return round(round(price / tick_size) * tick_size, 2)


def validate_symbol_token(token: str) -> Tuple[bool, Optional[str]]:
    """Validate a symbol token is a non-empty numeric string."""
    if not token or not token.strip():
        return False, "Symbol token is empty"
    if not token.isdigit():
        return False, f"Symbol token must be numeric, got: {token}"
    return True, None


def validate_position_value(
    quantity: int,
    price: float,
    max_position_value: float = 500000
) -> Tuple[bool, Optional[str]]:
    """Validate that position value does not exceed limits."""
    value = abs(quantity * price)
    if value > max_position_value:
        return False, f"Position value ₹{value:,.0f} exceeds limit ₹{max_position_value:,.0f}"
    return True, None

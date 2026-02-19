from fastapi import APIRouter, Depends, HTTPException
import os
import time
from src.api.schemas.orders import PlaceOrderRequest, OrderResponse
from src.api.dependencies import get_execution_client
from src.adapters.angel.execution_client import AngelExecutionClient
from src.engine.config_loader import load_risk_limits
from src.risk.position_sizer import PositionSizer
from src.utils.time_utils import is_market_open
from src.observability.metrics import ORDER_LATENCY, ORDERS_PLACED, ORDERS_REJECTED

router = APIRouter()

_position_sizer = None


def _get_position_sizer() -> PositionSizer:
    global _position_sizer
    if _position_sizer is None:
        risk_cfg = load_risk_limits()
        capital = float(os.getenv("PAPER_CAPITAL", "1000000"))
        _position_sizer = PositionSizer(total_capital=capital)
        _position_sizer.config = risk_cfg
        _position_sizer.position_limits = risk_cfg.get("position_limits", {})
        _position_sizer.product_config = risk_cfg.get("product_types", {})
        _position_sizer.fno_config = risk_cfg.get("fno", {})
        _position_sizer.lot_sizes = _position_sizer.fno_config.get("lot_sizes", {})
    return _position_sizer


def _normalize_product_type(product_type: str) -> str:
    mapping = {
        "INTRADAY": "MIS",
        "DELIVERY": "CNC",
        "CARRYFORWARD": "NRML",
        "MARGIN": "NRML",
    }
    return mapping.get(product_type, product_type)


def _raise_order_error(exchange: str, code: str, message: str, status_code: int = 400):
    ORDERS_REJECTED.labels(exchange=exchange, reason=code).inc()
    raise HTTPException(status_code=status_code, detail={"error_code": code, "message": message})


def _validate_order_for_paper(order: PlaceOrderRequest):
    enforce_guards = os.getenv("ENFORCE_ORDER_GUARDS", "false").lower() == "true"
    if not enforce_guards:
        return

    allow_off_market = os.getenv("ALLOW_OFF_MARKET_ORDERS", "false").lower() == "true"
    if not allow_off_market and not is_market_open():
        _raise_order_error(order.exchange, "MARKET_CLOSED", "Market is closed")

    if order.quantity <= 0:
        _raise_order_error(order.exchange, "INVALID_QUANTITY", "Quantity must be positive")

    order_type = order.ordertype.value
    product_type = _normalize_product_type(order.producttype.value)
    validation_price = float(order.price or 0)

    if order_type in {"MARKET", "STOPLOSS_MARKET"} and validation_price <= 0:
        fallback_price = float(os.getenv("MARKET_ORDER_REFERENCE_PRICE", "0") or 0)
        if fallback_price <= 0:
            _raise_order_error(
                order.exchange,
                "MISSING_REFERENCE_PRICE",
                "Risk guards require MARKET_ORDER_REFERENCE_PRICE for market-order validation",
            )
        validation_price = fallback_price

    if order_type in {"LIMIT", "STOPLOSS_LIMIT"} and validation_price <= 0:
        _raise_order_error(order.exchange, "INVALID_PRICE", "Price must be positive for limit/SL orders")

    sizer = _get_position_sizer()
    ok, err = sizer.validate_order(order.quantity, validation_price, product_type)
    if not ok:
        _raise_order_error(order.exchange, "RISK_VALIDATION_FAILED", err or "Risk validation failed")

@router.post("/", response_model=OrderResponse)
async def place_order(
    order: PlaceOrderRequest,
    client: AngelExecutionClient = Depends(get_execution_client)
):
    start_ts = time.perf_counter()
    try:
        _validate_order_for_paper(order)
        order_id = await client.place_order(
            trading_symbol=order.tradingsymbol,
            symbol_token=order.symboltoken,
            transaction_type=order.transactiontype.value,
            exchange=order.exchange,
            order_type=order.ordertype.value,
            product_type=order.producttype.value,
            duration=order.duration.value,
            price=order.price,
            quantity=order.quantity,
            trigger_price=order.triggerprice or 0,
            variety=order.variety
        )
        
        if order_id:
            ORDERS_PLACED.labels(
                exchange=order.exchange,
                order_type=order.ordertype.value,
                product_type=order.producttype.value,
                side=order.transactiontype.value,
            ).inc()
            ORDER_LATENCY.labels(exchange=order.exchange).observe(time.perf_counter() - start_ts)
            return OrderResponse(order_id=order_id, status="placed")
        else:
            ORDER_LATENCY.labels(exchange=order.exchange).observe(time.perf_counter() - start_ts)
            _raise_order_error(order.exchange, "BROKER_PLACE_FAILED", "Order placement failed")
            
    except HTTPException:
        ORDER_LATENCY.labels(exchange=order.exchange).observe(time.perf_counter() - start_ts)
        raise
    except Exception as e:
        ORDER_LATENCY.labels(exchange=order.exchange).observe(time.perf_counter() - start_ts)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/book")
async def get_order_book(client: AngelExecutionClient = Depends(get_execution_client)):
    return await client.get_order_book()

@router.get("/{order_id}")
async def get_order_status(order_id: str, client: AngelExecutionClient = Depends(get_execution_client)):
    order = await client.get_order_status(order_id)
    if not order:
        _raise_order_error("NSE", "ORDER_NOT_FOUND", f"Order {order_id} not found", status_code=404)
    return order

@router.delete("/{order_id}")
async def cancel_order(order_id: str, variety: str = "NORMAL", client: AngelExecutionClient = Depends(get_execution_client)):
    success = await client.cancel_order(order_id, variety)
    if success:
        return {"status": "cancelled", "order_id": order_id}
    _raise_order_error("NSE", "BROKER_CANCEL_FAILED", "Order cancellation failed")

@router.get("/trades/book")
async def get_trade_book(client: AngelExecutionClient = Depends(get_execution_client)):
    return await client.get_trade_book()

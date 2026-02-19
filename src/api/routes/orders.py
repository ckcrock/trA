from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict
from src.api.schemas.orders import PlaceOrderRequest, OrderResponse
from src.api.dependencies import get_execution_client
from src.adapters.angel.execution_client import AngelExecutionClient

router = APIRouter()

@router.post("/", response_model=OrderResponse)
async def place_order(
    order: PlaceOrderRequest,
    client: AngelExecutionClient = Depends(get_execution_client)
):
    try:
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
            return OrderResponse(order_id=order_id, status="placed")
        else:
            raise HTTPException(status_code=400, detail="Order placement failed")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/book")
async def get_order_book(client: AngelExecutionClient = Depends(get_execution_client)):
    return await client.get_order_book()

@router.get("/{order_id}")
async def get_order_status(order_id: str, client: AngelExecutionClient = Depends(get_execution_client)):
    order = await client.get_order_status(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order

@router.delete("/{order_id}")
async def cancel_order(order_id: str, variety: str = "NORMAL", client: AngelExecutionClient = Depends(get_execution_client)):
    success = await client.cancel_order(order_id, variety)
    if success:
        return {"status": "cancelled", "order_id": order_id}
    raise HTTPException(status_code=400, detail="Order cancellation failed")

@router.get("/trades/book")
async def get_trade_book(client: AngelExecutionClient = Depends(get_execution_client)):
    return await client.get_trade_book()

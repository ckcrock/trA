from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "STOPLOSS_LIMIT"
    STOPLOSS_MARKET = "STOPLOSS_MARKET"

class ProductType(str, Enum):
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    CARRYFORWARD = "CARRYFORWARD"

class Duration(str, Enum):
    DAY = "DAY"
    IOC = "IOC"

class PlaceOrderRequest(BaseModel):
    tradingsymbol: str
    symboltoken: str
    transactiontype: TransactionType
    exchange: str = "NSE"
    ordertype: OrderType
    producttype: ProductType
    duration: Duration = Duration.DAY
    price: float = Field(default=0.0, ge=0.0)
    quantity: int = Field(gt=0)
    triggerprice: Optional[float] = Field(default=None, ge=0.0)
    variety: str = "NORMAL"

class OrderResponse(BaseModel):
    order_id: str
    status: str
    message: Optional[str] = None

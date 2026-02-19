import logging
from typing import Dict, Any, List, Optional
from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
from src.adapters.angel.response_normalizer import normalize_smartapi_response, extract_order_id

logger = logging.getLogger(__name__)

class AngelExecutionClient:
    """
    Client for order execution and management.
    
    Reference: docs/angle/angel_one_complete_integration.py (AngelOrderManager, AngelPortfolio)
    """
    
    # Order varieties
    VARIETY_NORMAL = "NORMAL"
    VARIETY_STOPLOSS = "STOPLOSS"
    VARIETY_AMO = "AMO"
    
    # Transaction types
    TRANSACTION_BUY = "BUY"
    TRANSACTION_SELL = "SELL"
    
    # Order types
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_SL = "STOPLOSS_LIMIT"
    ORDER_TYPE_SL_M = "STOPLOSS_MARKET"
    
    # Product types
    PRODUCT_DELIVERY = "DELIVERY"
    PRODUCT_INTRADAY = "INTRADAY"
    PRODUCT_CARRYFORWARD = "CARRYFORWARD"
    
    # Duration
    DURATION_DAY = "DAY"
    DURATION_IOC = "IOC"

    VALID_EXCHANGES = {"NSE", "BSE", "NFO", "MCX"}
    VALID_TRANSACTION_TYPES = {TRANSACTION_BUY, TRANSACTION_SELL}
    VALID_ORDER_TYPES = {ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT, ORDER_TYPE_SL, ORDER_TYPE_SL_M}
    VALID_PRODUCTS = {PRODUCT_DELIVERY, PRODUCT_INTRADAY, PRODUCT_CARRYFORWARD, "MARGIN"}
    VALID_VARIETIES = {VARIETY_NORMAL, VARIETY_STOPLOSS, VARIETY_AMO}
    
    def __init__(self, auth_manager: AngelAuthManager, rate_limiter: TokenBucketRateLimiter):
        self.auth = auth_manager
        self.rate_limiter = rate_limiter

    def _validate_place_order_inputs(
        self,
        trading_symbol: str,
        symbol_token: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: float,
        trigger_price: float,
        variety: str,
    ) -> Optional[str]:
        if not trading_symbol or not isinstance(trading_symbol, str):
            return "Invalid trading symbol"
        if not str(symbol_token).strip().isdigit():
            return "Invalid symbol token"
        if exchange not in self.VALID_EXCHANGES:
            return f"Invalid exchange: {exchange}"
        if transaction_type not in self.VALID_TRANSACTION_TYPES:
            return f"Invalid transaction type: {transaction_type}"
        if order_type not in self.VALID_ORDER_TYPES:
            return f"Invalid order type: {order_type}"
        if product_type not in self.VALID_PRODUCTS:
            return f"Invalid product type: {product_type}"
        if variety not in self.VALID_VARIETIES:
            return f"Invalid variety: {variety}"
        if int(quantity) <= 0:
            return "Quantity must be positive"
        if order_type in {self.ORDER_TYPE_LIMIT, self.ORDER_TYPE_SL} and float(price) <= 0:
            return "Price must be positive for LIMIT/STOPLOSS_LIMIT"
        if order_type in {self.ORDER_TYPE_SL, self.ORDER_TYPE_SL_M} and float(trigger_price) <= 0:
            return "Trigger price must be positive for stop-loss orders"
        return None
        
    async def place_order(
        self,
        trading_symbol: str,
        symbol_token: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        price: float = 0,
        trigger_price: float = 0,
        variety: str = "NORMAL",
        duration: str = "DAY"
    ) -> Optional[str]:
        """
        Place an order.
        
        Args:
            trading_symbol: e.g., "SBIN-EQ", "NIFTY28FEB2425000CE"
            symbol_token: Instrument token
            exchange: NSE, BSE, NFO, MCX
            transaction_type: BUY or SELL
            quantity: Number of shares/contracts
            order_type: MARKET, LIMIT, STOPLOSS_LIMIT, STOPLOSS_MARKET
            product_type: DELIVERY, INTRADAY, CARRYFORWARD
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            variety: NORMAL, STOPLOSS, AMO
            duration: DAY, IOC
        
        Returns:
            Order ID if successful, None otherwise
        """
        validation_error = self._validate_place_order_inputs(
            trading_symbol=trading_symbol,
            symbol_token=symbol_token,
            exchange=exchange,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            product_type=product_type,
            price=price,
            trigger_price=trigger_price,
            variety=variety,
        )
        if validation_error:
            logger.error("Order validation failed: %s", validation_error)
            return None

        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            
            order_params = {
                "variety": variety,
                "tradingsymbol": trading_symbol,
                "symboltoken": symbol_token,
                "transactiontype": transaction_type,
                "exchange": exchange,
                "ordertype": order_type,
                "producttype": product_type,
                "duration": duration,
                "quantity": str(quantity)
            }
            
            # Add price for limit orders
            if order_type in [self.ORDER_TYPE_LIMIT, self.ORDER_TYPE_SL]:
                order_params["price"] = str(price)
            
            # Add trigger price for stop-loss orders
            if order_type in [self.ORDER_TYPE_SL, self.ORDER_TYPE_SL_M]:
                order_params["triggerprice"] = str(trigger_price)
            
            logger.info(f"ðŸ“¤ Placing order: {transaction_type} {quantity} {trading_symbol} @ {order_type}")
            
            response = client.placeOrder(order_params)
            normalized = normalize_smartapi_response(response)
            order_id = extract_order_id(response)
            if normalized["ok"] and order_id:
                logger.info(f"Order placed successfully! Order ID: {order_id}")
                return order_id

            error_msg = normalized["message"] or "Unknown error"
            logger.error(f"Order placement failed: {error_msg}")
            return None
                
        except Exception as e:
            logger.error(f"âŒ Order placement exception: {e}")
            return None

    async def modify_order(
        self,
        order_id: str,
        variety: str,
        quantity: int = None,
        order_type: str = None,
        price: float = None,
        trigger_price: float = None
    ) -> bool:
        """Modify an existing order."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            
            modify_params = {
                "variety": variety,
                "orderid": order_id,
            }
            
            if quantity:
                modify_params["quantity"] = str(quantity)
            if order_type:
                modify_params["ordertype"] = order_type
            if price:
                modify_params["price"] = str(price)
            if trigger_price:
                modify_params["triggerprice"] = str(trigger_price)
            
            logger.info(f"âœï¸ Modifying order: {order_id}")
            
            response = client.modifyOrder(modify_params)
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                logger.info(f"âœ… Order modified successfully!")
                return True
            else:
                error_msg = normalized["message"] or "Unknown error"
                logger.error(f"âŒ Order modification failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"âŒ Order modification exception: {e}")
            return False

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> bool:
        """Cancel an open order."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            
            logger.info(f"âŒ Canceling order: {order_id}")
            
            response = client.cancelOrder(order_id, variety)
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                logger.info(f"âœ… Order canceled successfully!")
                return True
            else:
                error_msg = normalized["message"] or "Unknown error"
                logger.error(f"âŒ Order cancellation failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"âŒ Order cancellation exception: {e}")
            return False

    async def get_order_book(self) -> List[Dict]:
        """Get all orders for the day."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.orderBook()
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                orders = normalized["data"] or []
                logger.info(f"ðŸ“‹ Fetched {len(orders)} orders")
                return orders
            return []
        except Exception as e:
            logger.error(f"âŒ Error fetching order book: {e}")
            return []

    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of a specific order."""
        orders = await self.get_order_book()
        for order in orders:
            if order.get('orderid') == order_id:
                return order
        logger.warning(f"âš ï¸ Order {order_id} not found")
        return None

    async def get_trade_book(self) -> List[Dict]:
        """Get all executed trades for the day."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.tradeBook()
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                trades = normalized["data"] or []
                logger.info(f"ðŸ“Š Fetched {len(trades)} trades")
                return trades
            return []
        except Exception as e:
            logger.error(f"âŒ Error fetching trade book: {e}")
            return []

    async def get_positions(self) -> Dict:
        """Get all open positions (intraday + overnight)."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.position()
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                positions = normalized["data"] or {}
                net = positions.get('net', [])
                day = positions.get('day', [])
                logger.info(f"ðŸ“Š Fetched {len(net)} net positions, {len(day)} day positions")
                return {'net': net, 'day': day}
            return {'net': [], 'day': []}
        except Exception as e:
            logger.error(f"âŒ Error fetching positions: {e}")
            return {'net': [], 'day': []}

    async def get_holdings(self) -> List[Dict]:
        """Get all delivery holdings."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.holding()
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                holdings = normalized["data"] or []
                logger.info(f"ðŸ“¦ Fetched {len(holdings)} holdings")
                return holdings
            return []
        except Exception as e:
            logger.error(f"âŒ Error fetching holdings: {e}")
            return []

    async def get_rms_limits(self) -> Optional[Dict]:
        """Get RMS (Risk Management System) limits / available margin."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.rmsLimit()
            normalized = normalize_smartapi_response(response)
            if normalized["ok"]:
                limits = normalized["data"] or {}
                logger.info(f"ðŸ’° Fetched RMS limits")
                return limits
            return None
        except Exception as e:
            logger.error(f"âŒ Error fetching RMS limits: {e}")
            return None



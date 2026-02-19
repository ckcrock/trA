import logging
from typing import Dict, Any, List, Optional
from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter

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
    
    def __init__(self, auth_manager: AngelAuthManager, rate_limiter: TokenBucketRateLimiter):
        self.auth = auth_manager
        self.rate_limiter = rate_limiter
        
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
            
            logger.info(f"📤 Placing order: {transaction_type} {quantity} {trading_symbol} @ {order_type}")
            
            response = client.placeOrder(order_params)
            
            if response and response.get('status'):
                order_id = response.get('data', {}).get('orderid')
                logger.info(f"✅ Order placed successfully! Order ID: {order_id}")
                return order_id
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Order placement failed: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Order placement exception: {e}")
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
            
            logger.info(f"✏️ Modifying order: {order_id}")
            
            response = client.modifyOrder(modify_params)
            
            if response and response.get('status'):
                logger.info(f"✅ Order modified successfully!")
                return True
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Order modification failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Order modification exception: {e}")
            return False

    async def cancel_order(self, order_id: str, variety: str = "NORMAL") -> bool:
        """Cancel an open order."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            
            logger.info(f"❌ Canceling order: {order_id}")
            
            response = client.cancelOrder(order_id, variety)
            
            if response and response.get('status'):
                logger.info(f"✅ Order canceled successfully!")
                return True
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Order cancellation failed: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Order cancellation exception: {e}")
            return False

    async def get_order_book(self) -> List[Dict]:
        """Get all orders for the day."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.orderBook()
            
            if response and response.get('status'):
                orders = response.get('data', [])
                logger.info(f"📋 Fetched {len(orders)} orders")
                return orders
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching order book: {e}")
            return []

    async def get_order_status(self, order_id: str) -> Optional[Dict]:
        """Get status of a specific order."""
        orders = await self.get_order_book()
        for order in orders:
            if order.get('orderid') == order_id:
                return order
        logger.warning(f"⚠️ Order {order_id} not found")
        return None

    async def get_trade_book(self) -> List[Dict]:
        """Get all executed trades for the day."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.tradeBook()
            
            if response and response.get('status'):
                trades = response.get('data', [])
                logger.info(f"📊 Fetched {len(trades)} trades")
                return trades
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching trade book: {e}")
            return []

    async def get_positions(self) -> Dict:
        """Get all open positions (intraday + overnight)."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.position()
            
            if response and response.get('status'):
                positions = response.get('data', {})
                net = positions.get('net', [])
                day = positions.get('day', [])
                logger.info(f"📊 Fetched {len(net)} net positions, {len(day)} day positions")
                return {'net': net, 'day': day}
            return {'net': [], 'day': []}
        except Exception as e:
            logger.error(f"❌ Error fetching positions: {e}")
            return {'net': [], 'day': []}

    async def get_holdings(self) -> List[Dict]:
        """Get all delivery holdings."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.holding()
            
            if response and response.get('status'):
                holdings = response.get('data', [])
                logger.info(f"📦 Fetched {len(holdings)} holdings")
                return holdings
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching holdings: {e}")
            return []

    async def get_rms_limits(self) -> Optional[Dict]:
        """Get RMS (Risk Management System) limits / available margin."""
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.rmsLimit()
            
            if response and response.get('status'):
                limits = response.get('data', {})
                logger.info(f"💰 Fetched RMS limits")
                return limits
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching RMS limits: {e}")
            return None

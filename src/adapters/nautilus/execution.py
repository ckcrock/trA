"""
Nautilus LiveExecutionClient for Angel One.
"""

import asyncio
from decimal import Decimal

try:
    from nautilus_trader.live.execution_client import LiveExecutionClient
    from nautilus_trader.model.identifiers import Venue, ClientId, AccountId
    from nautilus_trader.execution.messages import SubmitOrder, ModifyOrder, CancelOrder
    from nautilus_trader.common.component import MessageBus, Clock, Logger
    from nautilus_trader.cache.cache import Cache
    from nautilus_trader.model.enums import OrderStatus, OrderType
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes for type hinting
    class LiveExecutionClient: pass
    class Venue: pass
    class ClientId: pass
    class AccountId: pass
    class SubmitOrder: pass
    class ModifyOrder: pass
    class CancelOrder: pass
    class MessageBus: pass
    class Clock: pass
    class Cache: pass
    class Logger: pass
    class OrderStatus: pass
    class OrderType: pass


from src.adapters.angel.execution_client import AngelExecutionClient
from .config import AngelOneExecClientConfig
from .parsing import translate_order_type_to_angel
from .providers import AngelOneInstrumentProvider

class AngelOneExecutionClient(LiveExecutionClient):
    """
    Angel One Execution Client for NautilusTrader.
    Wraps AngelExecutionClient.
    """
    
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: AngelExecutionClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: Clock,
        instrument_provider: AngelOneInstrumentProvider,
        config: AngelOneExecClientConfig,
    ):
        if not NAUTILUS_AVAILABLE:
            return

        super().__init__(
            loop=loop,
            client_id=ClientId("ANGELONE-EXEC"),
            venue=Venue("ANGELONE"),
            oms_type=config.oms_type,
            account_type=config.account_type,
            base_currency=config.base_currency,
            instrument_provider=instrument_provider,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            config=config,
        )
        
        self._http = client
        self._provider = instrument_provider
        self._config = config
        
        self._account_id = AccountId(config.account_id or config.client_code or "ANGEL_ACC")

    @staticmethod
    def _to_str_enum(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return getattr(value, "name", str(value))

    @staticmethod
    def _to_float_price(value) -> float:
        if value is None:
            return 0.0
        try:
            if isinstance(value, Decimal):
                return float(value)
            if hasattr(value, "as_decimal"):
                return float(value.as_decimal())
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _to_int_qty(value) -> int:
        if value is None:
            return 0
        try:
            if isinstance(value, Decimal):
                return int(value)
            if hasattr(value, "as_decimal"):
                return int(value.as_decimal())
            return int(value)
        except Exception:
            return 0

    @staticmethod
    def _map_product_type(order) -> str:
        # Keep a conservative default for paper/live bridge mode.
        return "INTRADAY"

    def _connect(self):
        """Connect execution services."""
        self._loop.create_task(self._update_account_state())

    def _disconnect(self):
        return

    async def _update_account_state(self):
        """Fetch RMS limits and update account balance."""
        try:
            limits = await self._http.get_rms_limits()
            # Parse limits and publish AccountState
            pass
        except Exception as e:
            self._log.error(f"Error updating account state: {e}")

    def _submit_order(self, command: SubmitOrder):
        self._loop.create_task(self._submit_order_async(command))

    async def _submit_order_async(self, command: SubmitOrder):
        """Submit order to Angel One."""
        try:
            order = command.order
            instrument = self._provider.find(str(order.instrument_id))
            if not instrument:
                self._generate_order_rejected(command.order, reason="Instrument not found")
                return
                
            side_name = self._to_str_enum(getattr(order, "side", ""))
            if side_name not in {"BUY", "SELL"}:
                self._generate_order_rejected(command.order, reason=f"Unsupported side: {side_name}")
                return

            quantity = self._to_int_qty(getattr(order, "quantity", 0))
            if quantity <= 0:
                self._generate_order_rejected(command.order, reason="Invalid quantity")
                return

            order_type = translate_order_type_to_angel(getattr(order, "order_type", None))
            duration = "IOC" if self._to_str_enum(getattr(order, "time_in_force", "")) == "IOC" else "DAY"
            price = self._to_float_price(getattr(order, "price", 0))
            trigger = self._to_float_price(getattr(order, "trigger_price", 0))

            order_id = await self._http.place_order(
                trading_symbol=str(getattr(instrument, "raw_symbol", "")),
                symbol_token=str(getattr(instrument, "broker_symbol_token", "")),
                exchange=str(getattr(getattr(instrument, "venue", None), "value", "NSE")),
                transaction_type=side_name,
                quantity=quantity,
                order_type=order_type,
                product_type=self._map_product_type(order),
                price=price,
                trigger_price=trigger,
                variety="NORMAL",
                duration=duration,
            )

            if order_id:
                self._generate_order_accepted(command.order, venue_order_id=str(order_id))
            else:
                self._generate_order_rejected(command.order, reason="Broker rejected or no order id returned")
                
        except Exception as e:
            self._log.error(f"Error submitting order: {e}")
            self._generate_order_rejected(command.order, reason=str(e))

    def _cancel_order(self, command: CancelOrder):
        self._loop.create_task(self._cancel_order_async(command))

    async def _cancel_order_async(self, command: CancelOrder):
        """Cancel order."""
        try:
            order_id = str(getattr(command, "venue_order_id", "") or getattr(command, "order_id", ""))
            if not order_id:
                return
            await self._http.cancel_order(order_id=order_id, variety="NORMAL")
        except Exception as e:
            self._log.error(f"Error cancelling order: {e}")

    def _modify_order(self, command: ModifyOrder):
        # Angel modify support requires full order details; keep no-op for now.
        self._log.warning("Modify order not implemented for AngelOneExecutionClient adapter yet")

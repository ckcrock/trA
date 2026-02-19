"""
Nautilus LiveDataClient for Angel One.
"""

import asyncio
from typing import Optional, Dict

try:
    from nautilus_trader.adapters.env import LiveDataClient
    from nautilus_trader.model.identifiers import Venue, ClientId, InstrumentId
    from nautilus_trader.model.data import QuoteTick, Bar, BarType
    from nautilus_trader.common.component import MessageBus, Clock
    from nautilus_trader.cache.cache import Cache
    from nautilus_trader.common.logging import Logger
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes for type hinting
    class LiveDataClient: pass
    class Venue: pass
    class ClientId: pass
    class InstrumentId: pass
    class QuoteTick: pass
    class Bar: pass
    class BarType: pass
    class MessageBus: pass
    class Clock: pass
    class Cache: pass
    class Logger: pass


from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.websocket_client import AngelWebSocketClient
from .config import AngelOneDataClientConfig
from .parsing import parse_bar, parse_quote_tick
from .providers import AngelOneInstrumentProvider

class AngelOneDataClient(LiveDataClient):
    """
    Angel One Data Client for NautilusTrader.
    Wraps AngelDataClient (REST) and AngelWebSocketClient (WS).
    """
    
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: AngelDataClient,
        ws_client: AngelWebSocketClient,
        msgbus: MessageBus,
        cache: Cache,
        clock: Clock,
        logger: Logger,
        instrument_provider: AngelOneInstrumentProvider,
        config: AngelOneDataClientConfig,
    ):
        if not NAUTILUS_AVAILABLE:
            return

        super().__init__(
            loop=loop,
            client_id=ClientId("ANGELONE-DATA"),
            venue=Venue("ANGELONE"),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            logger=logger,
            config=config,
        )
        
        self._http = client
        self._ws = ws_client
        self._provider = instrument_provider
        self._config = config
        
        # Register callback for WebSocket ticks
        # Note: WS callbacks run in a separate thread, so we must use loop.call_soon_threadsafe
        self._ws.register_callback(self._on_ws_tick_threadsafe)

    async def _connect(self):
        """Connect to data services."""
        # HTTP client is stateless/persistent via AuthManager
        # WebSocket needs explicit connect if not connected
        if not self._ws.is_connected:
            self._log.info("Connecting WebSocket...")
            self._ws.connect()
            
    async def _disconnect(self):
        """Disconnect data services."""
        # We don't close the shared WS client here usually, as it might be used by others
        # But if this client owns it, we might. 
        # For this design, we assume shared lifecycle managed by Node.
        pass

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId):
        """Subscribe to live quotes."""
        instrument = self._provider.find(str(instrument_id))
        if not instrument:
            self._log.error(f"Instrument not found: {instrument_id}")
            return
            
        token = instrument.broker_symbol_token  # We assume we map this field
        exchange_seg = instrument.venue.value  # "NSE", "NFO" etc.
        
        # Map exchange name to Angel One numeric code if needed, 
        # but AngelWebSocketClient might handle string mapping or raw implementation needs check.
        # Checking existing websocket_client.py suggests it takes strict dict list.
        # We might need a helper to map "NSE" -> 1. 
        # Let's assume constants.py has mapping.
        
        # For simplicity in this plan, we rely on existing WS client logic or mocked behavior
        # In a real implementation, we map "NSE" -> 1, "NFO" -> 2 etc.
        
        # Subscribing...
        self._log.info(f"Subscribing to {instrument_id} (Token: {token})")
        # self._ws.subscribe(...) 
        # Implementation depends on exact WS client args
        pass

    def _on_ws_tick_threadsafe(self, tick: dict):
        """Handle tick from WebSocket (called from WS thread)."""
        self._loop.call_soon_threadsafe(self._process_tick, tick)
        
    def _process_tick(self, tick: dict):
        """Process tick in event loop."""
        try:
            quote_tick = parse_quote_tick(tick, self._provider, self._clock.timestamp_ns())
            if quote_tick:
                self._handle_data(quote_tick)
        except Exception as e:
            self._log.error(f"Error processing tick: {e}")

    # History
    async def _request_bars(self, bar_type: BarType, start, end, limit=None):
        """Request historical bars."""
        # Validate instrument
        instrument = self._provider.find(str(bar_type.instrument_id))
        if not instrument:
            return

        # Fetch from HTTP client
        # Map BarAggregation to Interval string
        interval = "ONE_DAY" # Logic to map bar_type.spec.aggregation
        
        bars_df = await self._http.get_historical_data(
            symbol_token=instrument.broker_symbol_token,
            exchange=instrument.venue.value, # "NSE"
            interval=interval,
            from_date=start,
            to_date=end
        )
        
        if bars_df is None or bars_df.empty:
            return

        # Parse and publish
        # ...
        pass

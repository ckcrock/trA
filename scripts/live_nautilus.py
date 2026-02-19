import asyncio
import os
import sys
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Path setup
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger("LivePaperTest")

try:
    import nautilus_trader
    from nautilus_trader.live.node import TradingNode
    from nautilus_trader.config import TradingNodeConfig, LiveDataClientConfig
    from nautilus_trader.live.config import RoutingConfig
    from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol, TraderId, ClientId
    from nautilus_trader.model.objects import Money, Currency, Price, Quantity
    from nautilus_trader.model.instruments import Equity
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.live.data_client import LiveDataClient
    from nautilus_trader.live.factories import LiveDataClientFactory
    
    logger.debug(f"DEBUG: nautilus_trader file: {nautilus_trader.__file__}")
    logger.debug(f"DEBUG: Price type: {type(Price.from_str('1'))} from {Price.__module__}")
    
    NAUTILUS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Import error: {e}")
    NAUTILUS_AVAILABLE = False
    # Dummy classes to prevent NameError during class definition
    class LiveDataClient:
        def __init__(self, *args, **kwargs): pass
    class LiveDataClientFactory: pass
    class BarType: pass
    class Equity: pass
    class RoutingConfig: pass

# Project Imports
from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.websocket_client import AngelWebSocketClient
from src.strategies.nautilus.ema_cross import EMACross, EMACrossConfig

class ManualNSEClient(LiveDataClient):
    """
    Dummy data client to satisfy Nautilus routing for NSE venue.
    We feed data manually, so this client just accepts subscriptions.
    """
    def __init__(self, **kwargs):
        # LiveDataClient expects client_id, msgbus, cache, clock, venue, config
        super().__init__(**kwargs)
    
    def subscribe_bars(self, command):
        # We don't need to do anything here as data is pushed manually
        pass
        
    def _set_connected(self, value=True):
        self.is_connected = value

class ManualNSEClientFactory(LiveDataClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return ManualNSEClient(
            client_id=ClientId(name),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            venue=Venue("NSE"),
            config=config
        )

class LiveBarAggregator:
    """
    Simpler aggregator for live ticks into bars.
    In a full adapter, this is handled by the DataClient.
    """
    def __init__(self, bar_type: BarType, instrument: Equity, on_bar_callback, bar_cls, price_cls, quantity_cls):
        self.bar_type = bar_type
        self.instrument = instrument
        self.on_bar_callback = on_bar_callback
        self.Bar = bar_cls
        self.Price = price_cls
        self.Quantity = quantity_cls
        self.current_bar = None
        self.bar_interval_seconds = 60 # Default 1m

    def handle_tick(self, msg):
        try:
            # SmartWebSocketV2 message format
            # LTP is in paise (Price * 100)
            ltp = float(msg.get('last_traded_price', 0)) / 100
            ts_ms = int(msg.get('exchange_timestamp', 0))
            if ts_ms == 0:
                ts_ms = int(datetime.now().timestamp() * 1000)
            
            ts_ns = ts_ms * 1_000_000
            
            # Simple 1-minute bar logic
            bar_start_ns = (ts_ns // (self.bar_interval_seconds * 1_000_000_000)) * (self.bar_interval_seconds * 1_000_000_000)
            
            if self.current_bar and self.current_bar.ts_event != bar_start_ns:
                # Dispatch finished bar
                self.on_bar_callback(self.current_bar)
                self.current_bar = None

            if not self.current_bar:
                self.current_bar = self.Bar(
                    self.bar_type,
                    self.instrument.id,
                    bar_start_ns,
                    int(datetime.now().timestamp() * 1_000_000_000),
                    self.Price.from_str(f"{ltp:.2f}"),
                    self.Price.from_str(f"{ltp:.2f}"),
                    self.Price.from_str(f"{ltp:.2f}"),
                    self.Price.from_str(f"{ltp:.2f}"),
                    self.Quantity.from_str("0")
                )
            else:
                p = self.Price.from_str(f"{ltp:.2f}")
                self.current_bar = self.Bar(
                    self.current_bar.bar_type,
                    self.current_bar.instrument_id,
                    self.current_bar.ts_event,
                    self.current_bar.ts_init,
                    self.current_bar.open,
                    max(self.current_bar.high, p),
                    min(self.current_bar.low, p),
                    p,
                    self.current_bar.volume
                )
        except Exception as e:
            logger.error(f"Error aggregating tick: {e}")

async def main():
    if not NAUTILUS_AVAILABLE:
        logger.error("Nautilus Trader not installed.")
        return

    # 0. Parse Arguments
    parser = argparse.ArgumentParser(description="Nautilus Live Test")
    parser.add_argument("--duration", type=int, default=60, help="Run duration in seconds")
    parser.add_argument("--symbol", type=str, default="SBIN", help="Trading symbol")
    parser.add_argument("--token", type=str, default="3045", help="Symbol token")
    args = parser.parse_args()

    load_dotenv()
    
    # 1. Setup Auth
    api_key = os.getenv("ANGEL_API_KEY")
    auth = AngelAuthManager(
        api_key=api_key,
        client_code=os.getenv("ANGEL_CLIENT_CODE"),
        mpin=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    if not auth.login():
        return

    # 2. Setup Node
    manual_config = LiveDataClientConfig(
        routing=RoutingConfig(venues=frozenset(["NSE"]))
    )
    config = TradingNodeConfig(
        trader_id=TraderId("LIVE-TEST-001"),
        data_clients={"NSE-MANUAL": manual_config}
    )
    node = TradingNode(config=config)
    
    # Register the manual client factory
    node.add_data_client_factory("NSE-MANUAL", ManualNSEClientFactory)
    
    # 3. Define Instrument (Register in cache)
    instrument_id_str = f"{args.symbol}-EQ.NSE"
    instrument = Equity(
        instrument_id=InstrumentId.from_str(instrument_id_str),
        raw_symbol=Symbol(args.symbol),
        currency=Currency.from_str("INR"),
        price_precision=2,
        price_increment=Price.from_str("0.05"),
        lot_size=Quantity.from_str("1"),
        ts_event=0,
        ts_init=0
    )
    node.kernel.data_engine.process(instrument)

    # 4. Setup Bar Type
    bar_type_str = f"{instrument_id_str}-1-MINUTE-MID-EXTERNAL"
    bar_type_obj = BarType.from_str(bar_type_str)

    # 5. Add Strategy
    strat_config = EMACrossConfig(
        instrument_id=instrument_id_str,
        bar_type=bar_type_str,
        fast_period=5,
        slow_period=10,
        quantity=1
    )
    strategy = EMACross(strat_config)
    node.trader.add_strategy(strategy)
    
    # 6. Setup WebSocket & Aggregator
    ws_client = AngelWebSocketClient(auth)
    
    def on_bar(bar):
        logger.info(f"📊 New Bar: {bar}")
        node.kernel.data_engine.process(bar)

    aggregator = LiveBarAggregator(bar_type_obj, instrument, on_bar, Bar, Price, Quantity)
    ws_client.register_callback(aggregator.handle_tick)

    # 7. Run
    logger.warning("⚠️ SAFE MODE: Execution client not registered. No real orders will be placed.")
    node.build()
    node.run() # Starts run_async as a task
    
    # Connect WebSocket
    ws_thread = ws_client.connect_in_thread()
    
    # Wait for connection to stabilize
    await asyncio.sleep(2)
    
    # Subscribe (Mode 2 = QUOTE)
    ws_client.subscribe(mode=2, token_list=[{"exchangeType": 1, "tokens": [args.token]}])
    
    try:
        logger.info(f"🚀 Running live data stream for {args.duration} seconds...")
        await asyncio.sleep(args.duration)
    finally:
        logger.info("Stopping...")
        ws_client.close()
        node.stop()
        node.dispose()

if __name__ == "__main__":
    asyncio.run(main())

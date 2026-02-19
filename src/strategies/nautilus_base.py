"""
NautilusTrader Strategy Adapter.
Allows running strategies within the NautilusTrader environment.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal

try:
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.instruments import Instrument
    from nautilus_trader.model.enums import OrderSide, TimeInForce
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.config import StrategyConfig
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    class Strategy: pass
    class StrategyConfig: pass


logger = logging.getLogger(__name__)


class NautilusStrategyConfig(StrategyConfig):
    """Configuration for Nautilus strategies."""
    instrument_id: str
    bar_type: str
    quantity: int = 1
    params: Dict[str, Any] = {}


class NautilusBaseStrategy(Strategy):
    """
    Base class for NautilusTrader strategies in this project.
    Provides helper methods and standardized logging.
    """

    def __init__(self, config: NautilusStrategyConfig):
        super().__init__(config)
        if not NAUTILUS_AVAILABLE:
            raise ImportError("NautilusTrader is not installed.")

        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type_id = config.bar_type  # In Nautilus this is often an ID string or object
        self.qty = Decimal(config.quantity)
        self.params = config.params
        self.instrument: Optional[Instrument] = None

    def on_start(self):
        """Lifecycle hook: Strategy started."""
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument: {self.instrument_id}")
            self.stop()
            return
        
        # Subscribe to bars
        # Ensure we pass a BarType object
        if isinstance(self.bar_type_id, str):
             self.subscribe_bars(BarType.from_str(self.bar_type_id))
        else:
             self.subscribe_bars(self.bar_type_id)
        
        self.log.info(f"Strategy {self.__class__.__name__} started for {self.instrument_id}")

    def on_stop(self):
        """Lifecycle hook: Strategy stopped."""
        self.log.info(f"Strategy {self.__class__.__name__} stopped.")
        self.close_all_positions(self.instrument_id)

    def on_bar(self, bar: Bar):
        """Handle incoming bars."""
        pass

    def buy(self, quantity: Optional[Decimal] = None):
        """Helper to place a market buy order."""
        qty = quantity if quantity else self.qty
        qty_obj = self.instrument.make_qty(qty)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=qty_obj,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"BUY {qty} {self.instrument_id}")

    def sell(self, quantity: Optional[Decimal] = None):
        """Helper to place a market sell order."""
        qty = quantity if quantity else self.qty
        qty_obj = self.instrument.make_qty(qty)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=qty_obj,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"SELL {qty} {self.instrument_id}")

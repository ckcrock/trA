from decimal import Decimal
import logging
from typing import Optional

try:
    from nautilus_trader.config import StrategyConfig
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.enums import OrderSide, TimeInForce
    from nautilus_trader.model.identifiers import InstrumentId, Venue
    from nautilus_trader.model.instruments import Instrument
    from nautilus_trader.model.orders import Order
    from nautilus_trader.model.objects import Quantity
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.indicators.averages import ExponentialMovingAverage

    from nautilus_trader.core.message import Event
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    class StrategyConfig: pass
    class Strategy: pass
    class Bar: pass
    class BarType: pass
    class InstrumentId: pass
    class Instrument: pass
    class ExponentialMovingAverage:
        def __init__(self, *args, **kwargs):
            self.value = 0.0
            self.initialized = False
        def update(self, *args, **kwargs): pass
    class OrderSide: pass
    class TimeInForce: pass


logger = logging.getLogger(__name__)


class EMACrossConfig(StrategyConfig):
    instrument_id: str
    bar_type: str
    fast_period: int = 10
    slow_period: int = 20
    quantity: int = 1

class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        # Indicators
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)
        
        self.instrument: Optional[Instrument] = None

    def on_start(self):
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument: {self.instrument_id}")
            self.stop()
            return

        self.subscribe_bars(self.bar_type)
        self.log.info(f"Started EMA Cross Strategy for {self.instrument_id}")

    def on_bar(self, bar: Bar):
        self.fast_ema.update_raw(float(bar.close))
        self.slow_ema.update_raw(float(bar.close))

        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        # Check logic
        if self.fast_ema.value > self.slow_ema.value:
            # Buy signal
            if self.portfolio.is_flat(self.instrument_id):
                self.buy()
            elif self.portfolio.is_net_short(self.instrument_id):
                self.close_all_positions(self.instrument_id)
                self.buy()
        
        elif self.fast_ema.value < self.slow_ema.value:
            # Sell signal
            if self.portfolio.is_flat(self.instrument_id):
                self.sell()
            elif self.portfolio.is_net_long(self.instrument_id):
                self.close_all_positions(self.instrument_id)
                self.sell()

    def buy(self):
        qty = self.instrument.make_qty(self.config.quantity)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=qty,
            time_in_force=TimeInForce.GTC, # or DAY
        )
        self.submit_order(order)
        self.log.info(f"BUY Signal: Fast({self.fast_ema.value:.2f}) > Slow({self.slow_ema.value:.2f})")

    def sell(self):
        qty = self.instrument.make_qty(self.config.quantity)
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=qty,
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"SELL Signal: Fast({self.fast_ema.value:.2f}) < Slow({self.slow_ema.value:.2f})")

    def on_stop(self):
        self.close_all_positions(self.instrument_id)
        self.log.info("Strategy Stopped")


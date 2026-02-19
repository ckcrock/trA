"""
EMA Crossover Strategy for NautilusTrader.
Ported to use NautilusBaseStrategy.
"""

from decimal import Decimal
from typing import Optional

try:
    from nautilus_trader.model.data import Bar
    from nautilus_trader.indicators.averages import ExponentialMovingAverage
    from src.strategies.nautilus_base import NautilusBaseStrategy, NautilusStrategyConfig
except ImportError:
    class NautilusBaseStrategy: pass
    class NautilusStrategyConfig: pass
    class ExponentialMovingAverage: pass


class EMACrossoverConfig(NautilusStrategyConfig):
    fast_period: int = 10
    slow_period: int = 20


class EMACrossoverStrategy(NautilusBaseStrategy):
    """
    EMA Crossover Strategy (Nautilus Version).
    """

    def __init__(self, config: EMACrossoverConfig):
        super().__init__(config)
        
        # Indicators
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)

    def on_bar(self, bar: Bar):
        # Update indicators with closing price
        # Note: Nautilus indicators usually take raw floats or Decimals depending on version
        # Newer versions like typed objects. `bar.close` is a Price (decimal wrapper)
        self.fast_ema.update_raw(float(bar.close))
        self.slow_ema.update_raw(float(bar.close))

        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        # Core Logic
        fast = self.fast_ema.value
        slow = self.slow_ema.value
        
        if fast > slow:
            # Buy signal
            if self.portfolio.is_flat(self.instrument_id):
                self.buy()
            elif self.portfolio.is_net_short(self.instrument_id):
                self.close_all_positions(self.instrument_id)
                self.buy()
        
        elif fast < slow:
            # Sell signal
            if self.portfolio.is_flat(self.instrument_id):
                self.sell()
            elif self.portfolio.is_net_long(self.instrument_id):
                self.close_all_positions(self.instrument_id)
                self.sell()

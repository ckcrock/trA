import pandas as pd
from typing import List
from decimal import Decimal
from nautilus_trader.model.data import Bar
from src.strategies.nautilus_base import NautilusBaseStrategy, NautilusStrategyConfig
from src.strategies.indicators import rsi

class RSIStrategyConfig(NautilusStrategyConfig):
    rsi_period: int = 14
    oversold: int = 30
    overbought: int = 70

class NautilusRSIStrategy(NautilusBaseStrategy):
    """
    RSI Mean Reversion Strategy.
    Buys when RSI < Oversold, Sells when RSI > Overbought.
    """
    def __init__(self, config: RSIStrategyConfig):
        super().__init__(config)
        self.rsi_period = config.rsi_period
        self.oversold = config.oversold
        self.overbought = config.overbought
        self.prices: List[float] = []

    def on_bar(self, bar: Bar):
        # Buffer close prices
        self.prices.append(float(bar.close))
        
        # We need enough prices for RSI and EWM stabilization
        if len(self.prices) < self.rsi_period + 1:
            return
            
        # Limit buffer size for efficiency
        if len(self.prices) > 100:
            self.prices.pop(0)
            
        # Calculate RSI
        series = pd.Series(self.prices)
        rsi_values = rsi(series, self.rsi_period)
        current_rsi = rsi_values.iloc[-1]
        
        if pd.isna(current_rsi):
            return

        # Position logic
        pos = self.cache.position(self.instrument_id)
        
        if pos is None or pos.is_flat:
            if current_rsi < self.oversold:
                self.log.info(f"RSI {current_rsi:.2f} < {self.oversold} (Oversold) - BUY")
                self.buy()
            elif current_rsi > self.overbought:
                self.log.info(f"RSI {current_rsi:.2f} > {self.overbought} (Overbought) - SELL")
                self.sell()
        elif pos.is_long:
            if current_rsi > 50: # Simple exit at 50 for mean reversion
                self.log.info(f"RSI {current_rsi:.2f} > 50 - Closing Long")
                self.sell(pos.quantity)
        elif pos.is_short:
            if current_rsi < 50:
                self.log.info(f"RSI {current_rsi:.2f} < 50 - Closing Short")
                self.buy(pos.quantity)

import pandas as pd
from typing import List, Dict
from decimal import Decimal
from nautilus_trader.model.data import Bar
from src.strategies.nautilus_base import NautilusBaseStrategy, NautilusStrategyConfig
from src.strategies.indicators import supertrend

class SupertrendStrategyConfig(NautilusStrategyConfig):
    period: int = 10
    multiplier: float = 3.0

class NautilusSupertrendStrategy(NautilusBaseStrategy):
    """
    Supertrend Trend Following Strategy.
    Buys when price crosses above Supertrend line.
    Sells when price crosses below Supertrend line.
    """
    def __init__(self, config: SupertrendStrategyConfig):
        super().__init__(config)
        self.period = config.period
        self.multiplier = config.multiplier
        self.bars_buffer: List[Dict] = []

    def on_bar(self, bar: Bar):
        # Accumulate OHLC
        self.bars_buffer.append({
            "high": float(bar.high),
            "low": float(bar.low),
            "close": float(bar.close)
        })
        
        # Supertrend needs 'period' + some buffer (e.g. 50 bars)
        if len(self.bars_buffer) < self.period + 1:
            return
            
        if len(self.bars_buffer) > 100:
            self.bars_buffer.pop(0)
            
        # Calculate Supertrend
        df = pd.DataFrame(self.bars_buffer)
        st_df = supertrend(df, self.period, self.multiplier)
        
        # Get current and previous values to detect crossover
        current = st_df.iloc[-1]
        previous = st_df.iloc[-2]
        
        if pd.isna(current["supertrend"]) or pd.isna(previous["supertrend"]):
            return

        # Position logic
        pos = self.cache.position(self.instrument_id)
        
        # Breakout/Crossover logic
        # current["supertrend_direction"] is 1 for bullish, -1 for bearish
        if current["supertrend_direction"] == 1 and previous["supertrend_direction"] == -1:
            # Bullish Crossover
            if pos is not None and pos.is_short:
                self.log.info(f"Supertrend Crossover Bullish - Closing Short")
                self.buy(pos.quantity)
            
            if pos is None or pos.is_flat:
                self.log.info(f"Supertrend Crossover Bullish - BUY")
                self.buy()
                
        elif current["supertrend_direction"] == -1 and previous["supertrend_direction"] == 1:
            # Bearish Crossover
            if pos is not None and pos.is_long:
                self.log.info(f"Supertrend Crossover Bearish - Closing Long")
                self.sell(pos.quantity)
                
            if pos is None or pos.is_flat:
                self.log.info(f"Supertrend Crossover Bearish - SELL")
                self.sell()

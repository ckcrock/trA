import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

# Nautilus Imports (only for data type creation)
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Price, Quantity
from nautilus_trader.core.datetime import dt_to_unix_nanos

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.data_manager import HistoricalDataManager
from src.bridge.bar_aggregator import BarAggregator
from src.strategies.indicators import rsi

# PURE PYTHON MOCK STRATEGY (Avoids Nautilus Actor immutability)
class MockRSIStrategy:
    def __init__(self, rsi_period=14, oversold=30, overbought=70):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.prices = []
        self.log = MagicMock()
        self.cache = MagicMock()
    
    def on_bar(self, bar: Bar):
        # Buffer close prices (Logic copied from nautilus_rsi.py)
        self.prices.append(float(bar.close))
        
        if len(self.prices) < self.rsi_period + 1:
            return
            
        if len(self.prices) > 100:
            self.prices.pop(0)
            
        series = pd.Series(self.prices)
        rsi_values = rsi(series, self.rsi_period)
        current_rsi = rsi_values.iloc[-1]
        
        if pd.isna(current_rsi):
            return

        # Simple signal detection for test output
        if current_rsi < self.oversold:
            self.log.info(f"RSI {current_rsi:.2f} < {self.oversold} (Oversold) - BUY SIGNAL")
        elif current_rsi > self.overbought:
            self.log.info(f"RSI {current_rsi:.2f} > {self.overbought} (Overbought) - SELL SIGNAL")

async def run_pipeline():
    print("Starting Data Pipeline E2E Test...")
    
    # 1. Load Data
    dm = HistoricalDataManager()
    symbol = "SBIN"
    df = dm.load(symbol, "ONE_MINUTE")
    if df is None:
        print("No cached 1m data found, generating sample data...")
        df = dm.create_sample_data(symbol=symbol, days=5, interval_minutes=1)
    
    print(f"Loaded {len(df)} 1-minute bars.")

    # 2. Setup Aggregator (1m -> 5m)
    # interval is 300 seconds (5m)
    aggregator = BarAggregator(intervals=[300])
    
    # 3. Setup Mock Strategy
    strategy = MockRSIStrategy(rsi_period=14, oversold=30, overbought=70)
    
    # Helper objects for Bar conversion
    bar_type = BarType.from_str("SBIN.NSE-5-MINUTE-LAST-INTERNAL")

    async def strategy_callback(bar_dict):
        # Convert dict to Nautilus Bar (for a realistic test of on_bar signature)
        ts_event = dt_to_unix_nanos(datetime.fromisoformat(bar_dict["timestamp"]))
        n_bar = Bar(
            bar_type=bar_type,
            open=Price.from_str(str(bar_dict["open"])),
            high=Price.from_str(str(bar_dict["high"])),
            low=Price.from_str(str(bar_dict["low"])),
            close=Price.from_str(str(bar_dict["close"])),
            volume=Quantity.from_str(str(bar_dict["volume"])),
            ts_event=ts_event,
            ts_init=ts_event
        )
        
        strategy.on_bar(n_bar)
        
        # Check if log.info was called
        if strategy.log.info.called:
            for call in strategy.log.info.call_args_list:
                msg = call[0][0]
                print(f"[{bar_dict['timestamp']}] SIGNAL DETECTED: {msg}")
            strategy.log.info.reset_mock()

    aggregator.on_completed_bar(strategy_callback)

    # 4. Feed ticks (1m bars acting as ticks)
    print(f"Processing 1m bars as ticks for {symbol}...")
    
    # To ensure we get some signals, let's artificially vary the data if it's too flat
    # But usually sample data has enough variance.
    
    count = 0
    for _, row in df.iterrows():
        tick = {
            "symbol": symbol,
            "ltp": row["close"],
            "volume": row["volume"],
            "timestamp": row["timestamp"].isoformat() if isinstance(row["timestamp"], datetime) else row["timestamp"]
        }
        await aggregator.on_tick(tick)
        count += 1
        if count % 2000 == 0:
            print(f"Processed {count}/{len(df)} ticks...")
    
    # Final flush to process any remaining bars
    await aggregator.flush()
    
    print("\nPipeline E2E Test Completed Successfully.")
    stats = aggregator.get_stats()
    print(f"Aggregator Stats: Ticks={stats['ticks_processed']}, Bars Emitted={stats['bars_emitted']}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())

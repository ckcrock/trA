"""
Script to run NautilusTrader backtest with local data.
"""

import sys
import os
import asyncio
import logging
import pandas as pd
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtesting.nautilus_runner import NautilusRunner
from src.strategies.nautilus_ema import EMACrossoverStrategy, EMACrossoverConfig
from src.data.data_manager import HistoricalDataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NautilusRun")

def main():
    symbol = "SBIN"
    exchange = "NSE"
    
    # 1. Setup Data Manager
    data_manager = HistoricalDataManager()
    interval = "ONE_MINUTE" 
    
    # 2. Setup Runner
    runner = NautilusRunner(symbol=symbol, exchange=exchange)
    runner.setup(initial_capital=100_000)
    
    # 3. Load Data
    # Try loading from catalog first
    logger.info("Loading data from catalog...")
    success = runner.load_from_catalog(data_manager, symbol, interval)
    
    if not success:
        logger.info("Data not found in catalog. Generating sample data...")
        # Create sample data
        df = HistoricalDataManager.create_sample_data(symbol=symbol, days=30, interval_minutes=1)
        # Save to catalog so it's available next time
        data_manager.save(df, symbol, interval)
        logger.info("Sample data saved to catalog.")
        
        # Load again properly
        runner.load_from_catalog(data_manager, symbol, interval)
    
    # 4. Add Strategy
    config = EMACrossoverConfig(
        instrument_id=f"{symbol}-EQ.{exchange}",
        bar_type=f"{symbol}-EQ.{exchange}-1-MINUTE-MID-EXTERNAL",
        fast_period=10,
        slow_period=20,
        quantity=10
    )
    
    runner.add_strategy(EMACrossoverStrategy, config)
    
    # 5. Run & Stats
    runner.run()
    
    stats = runner.get_stats()
    print("\n" + "="*50)
    print("BACKTEST STATISTICS")
    print("="*50)
    print(stats)

if __name__ == "__main__":
    main()

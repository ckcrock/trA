"""
NautilusTrader Backtest Runner.
Encapsulates the setup and execution of a backtest using NautilusTrader.
"""

import logging
import asyncio
from typing import Dict, Any, Type, List, Optional
from datetime import datetime
import pandas as pd

try:
    from nautilus_trader.backtest.engine import BacktestEngine
    from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.identifiers import Venue, InstrumentId, Symbol, TraderId
    from nautilus_trader.model.objects import Money, Currency, Price, Quantity
    from nautilus_trader.model.enums import OmsType, AccountType
    from nautilus_trader.model.instruments import Equity, Instrument
    from nautilus_trader.test_kit.providers import TestInstrumentProvider
    from src.adapters.nautilus.parsing import parse_bar
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class NautilusRunner:
    """
    Runs backtests using NautilusTrader.
    """

    def __init__(self, symbol: str, exchange: str = "NSE", currency: str = "INR"):
        if not NAUTILUS_AVAILABLE:
            raise ImportError("NautilusTrader not installed.")
            
        self.symbol = symbol
        self.exchange = exchange
        self.currency = currency
        
        self.engine: Optional[BacktestEngine] = None
        self.instrument: Optional[Instrument] = None
        self.bars: List[Bar] = []
        self.bar_type: Optional[BarType] = None

    def setup(self, initial_capital: float = 1_000_000):
        """Initialize the engine and venue."""
        config = BacktestEngineConfig(
            trader_id=TraderId("BACKTESTER-001"),
            logging=LoggingConfig(log_level="INFO")
        )
        self.engine = BacktestEngine(config=config)

        # Add Venue
        self.engine.add_venue(
            venue=Venue(self.exchange),
            oms_type=OmsType.HEDGING,
            account_type=AccountType.MARGIN,
            starting_balances=[Money(initial_capital, Currency.from_str(self.currency))]
        )
        
        # Create and add Instrument
        self._define_instrument()
        self.engine.add_instrument(self.instrument)

    def _define_instrument(self):
        """Define the equity instrument."""
        instrument_id_str = f"{self.symbol}-EQ.{self.exchange}" 
        # Note: Nautilus expects ID format like "SIM-USD.SIM" or "AAPL.NASDAQ"
        # We use a simplified definition for backtesting
        
        self.instrument = Equity(
            instrument_id=InstrumentId.from_str(instrument_id_str),
            raw_symbol=Symbol(self.symbol),
            currency=Currency.from_str(self.currency),
            price_precision=2,
            price_increment=Price.from_str("0.05"),
            lot_size=Quantity.from_str("1"),
            ts_event=0,
            ts_init=0
        )

    def load_data(self, df: pd.DataFrame, interval: str = "ONE_MINUTE"):
        """
        Load historical data from a DataFrame and convert to Nautilus Bars.
        df expected to have: timestamp, open, high, low, close, volume
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not defined. Call setup() first.")
            
        logger.info(f"Converting {len(df)} rows to Nautilus Bars...")
        
        # Map interval string to integer definition for BarType
        # ONE_MINUTE -> 1 MINUTE
        # ONE_DAY -> 1 DAY
        period = 1
        unit = "MINUTE"
        if "DAY" in interval:
            unit = "DAY"
        elif "HOUR" in interval:
            unit = "HOUR"
            
        bar_type_str = f"{self.instrument.id}-{period}-{unit}-MID-EXTERNAL"
        self.bar_type = BarType.from_str(bar_type_str)

        self.bars = []
        for row in df.itertuples(index=False):
            # Ensure timestamp is pandas Timestamp or python datetime
            ts = row.timestamp
            
            # Simple conversion
            try:
                # Assuming row matches our standard OHLCV format
                candle = [ts, row.open, row.high, row.low, row.close, row.volume]
                bar = parse_bar(self.bar_type, candle, self.instrument, 0)
                if bar:
                    self.bars.append(bar)
            except Exception as e:
                logger.warning(f"Failed to parse row: {row} - {e}")
                
        logger.info(f"Loaded {len(self.bars)} bars.")
        self.engine.add_data(self.bars)

    def load_from_catalog(self, data_manager, symbol: str, interval: str):
        """Load data from the HistoricalDataManager catalog."""
        df = data_manager.load(symbol, interval)
        if df is None or df.empty:
            logger.warning(f"No data found for {symbol} {interval} in catalog.")
            return False
            
        logger.info(f"Loaded {len(df)} rows from catalog for {symbol}.")
        self.load_data(df, interval)
        return True

    def add_strategy(self, strategy_cls: Type, config: Dict[str, Any]):
        """Add a strategy to the engine."""
        if not self.engine:
            raise RuntimeError("Engine not initialized")
            
        # config needs to be a StrategyConfig object of the specific strategy
        # We assume the user passes the Config Class instance, or we create it?
        # Typically strategy_cls(config_instance)
        
        self.engine.add_strategy(strategy_cls(config))

    def run(self):
        """Run the backtest."""
        if not self.engine:
            raise RuntimeError("Engine not initialized")
        
        logger.info("Starting Backtest...")
        self.engine.run()
        logger.info("Backtest Finished.")

    def get_stats(self):
        """Return execution statistics."""
        result = self.engine.get_result()
        if result:
             # Return PnL stats as a basic report
             return result.stats_pnls
        return "No result available"

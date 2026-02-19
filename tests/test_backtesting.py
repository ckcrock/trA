"""
Tests for Backtesting Engine, Data Manager, and Bridge enhancements.
Run with: venv\\Scripts\\python -m pytest tests/test_backtesting.py -v
"""

import sys
import os
import asyncio
import tempfile
import pytest
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════
# Data Manager Tests
# ═══════════════════════════════════════════════════════════════════════


class TestHistoricalDataManager:
    """Tests for src.data.data_manager.HistoricalDataManager"""

    def test_save_and_load(self, tmp_path):
        """Save a DataFrame to Parquet, load it back, validate equality."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager(catalog_dir=str(tmp_path))

        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=100, freq="5min"),
            "open": np.random.uniform(490, 510, 100),
            "high": np.random.uniform(500, 520, 100),
            "low": np.random.uniform(480, 500, 100),
            "close": np.random.uniform(490, 510, 100),
            "volume": np.random.randint(1000, 50000, 100),
        })

        path = mgr.save(df, "TESTSTOCK", "FIVE_MINUTE")
        assert os.path.exists(path)

        loaded = mgr.load("TESTSTOCK", "FIVE_MINUTE")
        assert loaded is not None
        assert len(loaded) == 100
        assert list(loaded.columns) == list(df.columns)

    def test_load_nonexistent(self, tmp_path):
        """Loading a non-existent dataset returns None."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager(catalog_dir=str(tmp_path))
        result = mgr.load("NOSYMBOL", "ONE_DAY")
        assert result is None

    def test_list_available(self, tmp_path):
        """List shows saved datasets."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager(catalog_dir=str(tmp_path))

        df = pd.DataFrame({
            "timestamp": ["2024-01-01"],
            "open": [100], "high": [105], "low": [95], "close": [102], "volume": [1000],
        })
        mgr.save(df, "SBIN", "ONE_DAY")
        mgr.save(df, "RELIANCE", "FIVE_MINUTE")

        available = mgr.list_available()
        assert len(available) == 2
        symbols = {d["symbol"] for d in available}
        assert "SBIN" in symbols
        assert "RELIANCE" in symbols

    def test_validate_clean_data(self):
        """Validation passes for clean data."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager()
        df = HistoricalDataManager.create_sample_data(days=5)
        result = mgr.validate(df)
        assert result["valid"] == True
        assert result["duplicates"] == 0
        assert result["total_rows"] > 0

    def test_validate_bad_data(self):
        """Validation catches NaN and missing columns."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager()
        df = pd.DataFrame({"timestamp": [1, 2, 3], "open": [1, np.nan, 3], "close": [1, 2, 3]})
        result = mgr.validate(df)
        assert result["valid"] is False
        assert len(result["missing_columns"]) > 0  # Missing high, low, volume

    def test_create_sample_data(self):
        """Sample data generator produces valid OHLCV DataFrame."""
        from src.data.data_manager import HistoricalDataManager

        df = HistoricalDataManager.create_sample_data(days=10, interval_minutes=5)
        assert not df.empty
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns
        assert "timestamp" in df.columns
        assert (df["close"] > 0).all()

    def test_delete(self, tmp_path):
        """Delete removes cached file."""
        from src.data.data_manager import HistoricalDataManager

        mgr = HistoricalDataManager(catalog_dir=str(tmp_path))
        df = pd.DataFrame({
            "timestamp": ["2024-01-01"],
            "open": [100], "high": [105], "low": [95], "close": [102], "volume": [1000],
        })
        mgr.save(df, "TODELETE", "ONE_DAY")
        assert mgr.load("TODELETE", "ONE_DAY") is not None

        deleted = mgr.delete("TODELETE", "ONE_DAY")
        assert deleted is True
        assert mgr.load("TODELETE", "ONE_DAY") is None


# ═══════════════════════════════════════════════════════════════════════
# Backtesting Engine Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBacktestEngine:
    """Tests for src.backtesting.engine.BacktestEngine"""

    def _make_sample_data(self, bars=200):
        """Create simple synthetic bar data for testing."""
        from src.data.data_manager import HistoricalDataManager
        return HistoricalDataManager.create_sample_data(days=max(bars // 75, 5))

    def test_engine_runs_and_produces_result(self):
        """Engine processes bars and returns a BacktestResult."""
        from src.backtesting.engine import BacktestEngine, BacktestConfig
        from src.strategies.ema_crossover import EMACrossoverStrategy

        data = self._make_sample_data()
        strategy = EMACrossoverStrategy({
            "name": "test_ema",
            "fast_period": 9,
            "slow_period": 21,
            "quantity": 10,
        })

        engine = BacktestEngine(strategy, data, BacktestConfig(initial_capital=100_000))
        result = engine.run()

        assert result is not None
        assert result.strategy_name == "test_ema"
        assert result.total_bars == len(data)
        assert result.initial_capital == 100_000
        assert result.final_capital > 0
        assert len(result.equity_curve) == len(data)

    def test_pnl_calculation(self):
        """Verify P&L math with known data: constant up-trend should profit on BUY."""
        from src.backtesting.engine import BacktestEngine, BacktestConfig
        from src.strategies.base_strategy import BaseStrategy

        # Create a simple "buy immediately" strategy
        class AlwaysBuyStrategy(BaseStrategy):
            def __init__(self):
                super().__init__({"name": "always_buy"})
                self._bought = False

            def on_bar(self, bar):
                super().on_bar(bar)
                if not self._bought and self.bar_count >= 2:
                    self.generate_signal("BUY", bar["close"], "test buy")
                    self.submit_order("BUY", 10)
                    self._bought = True

        # Create data with a clear uptrend
        n = 50
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "open": [100 + i * 0.5 for i in range(n)],
            "high": [101 + i * 0.5 for i in range(n)],
            "low": [99 + i * 0.5 for i in range(n)],
            "close": [100.5 + i * 0.5 for i in range(n)],
            "volume": [10000] * n,
        })

        strategy = AlwaysBuyStrategy()
        config = BacktestConfig(initial_capital=50_000, commission_pct=0, slippage_pct=0)
        engine = BacktestEngine(strategy, df, config)
        result = engine.run()

        # Should be profitable: bought early in uptrend, force-closed at end
        assert result.total_pnl > 0
        assert result.total_return_pct > 0

    def test_backtest_with_ema_strategy(self):
        """Full integration: EMA crossover on sample data produces valid metrics."""
        from src.backtesting.engine import BacktestEngine, BacktestConfig
        from src.strategies.ema_crossover import EMACrossoverStrategy

        data = self._make_sample_data(bars=500)
        strategy = EMACrossoverStrategy({
            "name": "ema_test",
            "fast_period": 9,
            "slow_period": 21,
            "quantity": 5,
        })

        engine = BacktestEngine(strategy, data)
        result = engine.run()

        # Metrics should be computed
        assert isinstance(result.sharpe_ratio, float)
        assert isinstance(result.max_drawdown_pct, float)
        assert result.max_drawdown_pct >= 0
        assert 0 <= result.win_rate <= 100

        # Summary should be printable
        summary = result.summary()
        assert "ema_test" in summary
        assert "Sharpe" in summary

    def test_backtest_config_defaults(self):
        """BacktestConfig has reasonable defaults."""
        from src.backtesting.engine import BacktestConfig

        config = BacktestConfig()
        assert config.initial_capital == 100_000
        assert config.commission_pct > 0
        assert config.slippage_pct > 0
        assert config.risk_free_rate > 0


# ═══════════════════════════════════════════════════════════════════════
# Bridge Tests
# ═══════════════════════════════════════════════════════════════════════


class TestBarAggregator:
    """Tests for src.bridge.bar_aggregator.BarAggregator"""

    @pytest.mark.asyncio
    async def test_aggregator_emits_bars(self):
        """Feed ticks spanning two intervals, verify bar emission."""
        from src.bridge.bar_aggregator import BarAggregator

        emitted_bars = []

        async def on_bar(bar):
            emitted_bars.append(bar)

        aggregator = BarAggregator(intervals=[60])  # 1-minute bars
        aggregator.on_completed_bar(on_bar)

        # Send ticks across two 1-minute intervals
        ticks = [
            {"symbol": "SBIN", "ltp": 500.0, "volume": 100, "timestamp": "2024-01-01T09:15:00"},
            {"symbol": "SBIN", "ltp": 502.0, "volume": 200, "timestamp": "2024-01-01T09:15:30"},
            {"symbol": "SBIN", "ltp": 498.0, "volume": 150, "timestamp": "2024-01-01T09:15:45"},
            # This tick crosses into the next minute — should emit the first bar
            {"symbol": "SBIN", "ltp": 501.0, "volume": 300, "timestamp": "2024-01-01T09:16:05"},
        ]

        for tick in ticks:
            await aggregator.on_tick(tick)

        # First bar should have been emitted when 09:16 tick arrived
        assert len(emitted_bars) == 1
        bar = emitted_bars[0]
        assert bar["symbol"] == "SBIN"
        assert bar["open"] == 500.0
        assert bar["high"] == 502.0
        assert bar["low"] == 498.0
        assert bar["close"] == 498.0
        assert bar["tick_count"] == 3

    @pytest.mark.asyncio
    async def test_aggregator_flush(self):
        """Flush emits all active bars."""
        from src.bridge.bar_aggregator import BarAggregator

        emitted = []
        async def on_bar(bar):
            emitted.append(bar)

        aggregator = BarAggregator(intervals=[60])
        aggregator.on_completed_bar(on_bar)

        await aggregator.on_tick({"symbol": "X", "ltp": 100, "volume": 1, "timestamp": "2024-01-01T10:00:00"})
        assert len(emitted) == 0

        await aggregator.flush()
        assert len(emitted) == 1

    @pytest.mark.asyncio
    async def test_aggregator_stats(self):
        """Stats track ticks and bars."""
        from src.bridge.bar_aggregator import BarAggregator

        aggregator = BarAggregator(intervals=[60])
        await aggregator.on_tick({"symbol": "A", "ltp": 10, "volume": 1, "timestamp": "2024-01-01T09:00:00"})

        stats = aggregator.get_stats()
        assert stats["ticks_processed"] == 1
        assert stats["active_bars"] == 1


class TestDataBridge:
    """Tests for src.bridge.data_bridge.DataBridge enhancements."""

    def test_get_queue_utilization(self):
        """Queue utilization returns percentage."""
        from src.bridge.data_bridge import DataBridge

        bridge = DataBridge(max_queue_size=100)
        util = bridge.get_queue_utilization()
        assert util == 0.0

    def test_get_stats_includes_queue_size(self):
        """Stats dict includes queue_size key."""
        from src.bridge.data_bridge import DataBridge

        bridge = DataBridge()
        stats = bridge.get_stats()
        assert "queue_size" in stats
        assert "ticks_received" in stats
        assert "ticks_dropped" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

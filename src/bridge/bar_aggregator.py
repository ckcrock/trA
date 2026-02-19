"""
Bar Aggregator — accumulates ticks into OHLCV bars at configurable intervals.
Integrates as a DataBridge subscriber.
Reference: IMPLEMENTATION_ROADMAP.md §Phase 2
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Awaitable, Optional

logger = logging.getLogger(__name__)


class BarAggregator:
    """
    Accumulates live tick data into time-based OHLCV bars.

    Supports multiple intervals simultaneously (e.g. 1m, 5m, 15m).
    Emits completed bars to registered callbacks.

    Usage:
        aggregator = BarAggregator(intervals=[60, 300])  # 1m and 5m
        aggregator.on_completed_bar(my_callback)
        data_bridge.subscribe(aggregator.on_tick)
    """

    def __init__(self, intervals: List[int] = None):
        """
        Args:
            intervals: List of bar intervals in seconds.
                       Default: [60] (1-minute bars).
        """
        self.intervals = intervals or [60]
        self._callbacks: List[Callable[[Dict], Awaitable[None]]] = []

        # Active bar buckets keyed by (symbol, interval_seconds)
        self._bars: Dict[tuple, Dict] = {}

        self.stats = {
            "ticks_processed": 0,
            "bars_emitted": 0,
        }

        logger.info(f"📊 BarAggregator initialized (intervals={self.intervals}s)")

    def on_completed_bar(self, callback: Callable[[Dict], Awaitable[None]]):
        """Register an async callback for completed bars."""
        self._callbacks.append(callback)

    async def on_tick(self, tick: Dict):
        """
        Process a normalized tick from DataBridge.
        Accumulates into bar buckets and emits when interval boundary is crossed.
        """
        self.stats["ticks_processed"] += 1

        symbol = tick.get("symbol", "UNKNOWN")
        ltp = tick.get("ltp", 0)
        volume = tick.get("volume", 0)

        if ltp <= 0:
            return

        # Parse tick timestamp
        ts_raw = tick.get("timestamp")
        try:
            if isinstance(ts_raw, str):
                tick_time = datetime.fromisoformat(ts_raw)
            elif isinstance(ts_raw, (int, float)):
                tick_time = datetime.fromtimestamp(ts_raw)
            else:
                tick_time = datetime.now()
        except (ValueError, TypeError, OSError):
            tick_time = datetime.now()

        # Update bars for each interval
        for interval in self.intervals:
            key = (symbol, interval)
            bar_start = self._get_bar_start(tick_time, interval)

            if key not in self._bars:
                # Start a new bar
                self._bars[key] = self._new_bar(symbol, bar_start, interval, ltp, volume)
            else:
                current_bar = self._bars[key]
                current_bar_start = current_bar["bar_start"]

                if bar_start > current_bar_start:
                    # New interval boundary — emit the completed bar and start fresh
                    await self._emit_bar(current_bar)
                    self._bars[key] = self._new_bar(symbol, bar_start, interval, ltp, volume)
                else:
                    # Update existing bar
                    current_bar["high"] = max(current_bar["high"], ltp)
                    current_bar["low"] = min(current_bar["low"], ltp)
                    current_bar["close"] = ltp
                    current_bar["volume"] += volume
                    current_bar["tick_count"] += 1

    # ─── Internal Helpers ────────────────────────────────────────────

    @staticmethod
    def _get_bar_start(tick_time: datetime, interval_seconds: int) -> datetime:
        """Align a timestamp to the start of its bar interval."""
        epoch = datetime(tick_time.year, tick_time.month, tick_time.day)
        seconds_since_midnight = (tick_time - epoch).total_seconds()
        bar_seconds = int(seconds_since_midnight // interval_seconds) * interval_seconds
        return epoch + timedelta(seconds=bar_seconds)

    @staticmethod
    def _new_bar(symbol: str, bar_start: datetime, interval: int,
                 price: float, volume: int) -> Dict:
        """Create a new bar bucket."""
        return {
            "symbol": symbol,
            "bar_start": bar_start,
            "interval_seconds": interval,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
            "tick_count": 1,
        }

    async def _emit_bar(self, bar: Dict):
        """Emit a completed bar to all registered callbacks."""
        self.stats["bars_emitted"] += 1

        # Format for output
        output_bar = {
            "symbol": bar["symbol"],
            "timestamp": bar["bar_start"].isoformat(),
            "interval_seconds": bar["interval_seconds"],
            "open": bar["open"],
            "high": bar["high"],
            "low": bar["low"],
            "close": bar["close"],
            "volume": bar["volume"],
            "tick_count": bar["tick_count"],
        }

        logger.debug(f"📊 Bar completed: {output_bar['symbol']} "
                      f"{output_bar['interval_seconds']}s | "
                      f"O={output_bar['open']:.2f} H={output_bar['high']:.2f} "
                      f"L={output_bar['low']:.2f} C={output_bar['close']:.2f}")

        if self._callbacks:
            tasks = [cb(output_bar) for cb in self._callbacks]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def flush(self):
        """Flush all open bars (e.g. at market close)."""
        for key in list(self._bars.keys()):
            await self._emit_bar(self._bars[key])
        self._bars.clear()

    def get_stats(self) -> Dict:
        """Get aggregator statistics."""
        return {
            **self.stats,
            "active_bars": len(self._bars),
        }

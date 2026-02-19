"""
Bridge adapter to convert DataBridge ticks to Nautilus QuoteTicks.
Provides integration point between the live data pipeline and Nautilus DataEngine.
Reference: nautilus_broker_bridge_architecture.md
"""

import logging
from datetime import datetime
from typing import Optional, Any

try:
    from nautilus_trader.model.data import QuoteTick
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.objects import Price, Quantity
    from nautilus_trader.core.datetime import dt_to_unix_nanos
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class NautilusBridgeAdapter:
    """
    Converts normalized ticks from DataBridge to Nautilus QuoteTick objects
    and pushes them to a Nautilus DataEngine.

    Usage:
        adapter = NautilusBridgeAdapter(instrument_provider)
        adapter.set_data_engine(node.data_engine)
        data_bridge.subscribe(adapter.on_tick)
    """

    def __init__(self, instrument_provider=None):
        self.instrument_provider = instrument_provider
        self._data_engine = None
        self._tick_count = 0
        self._error_count = 0

    def set_data_engine(self, data_engine):
        """
        Set the Nautilus DataEngine to push converted ticks to.

        Args:
            data_engine: NautilusTrader DataEngine instance
        """
        self._data_engine = data_engine
        logger.info("✅ NautilusBridgeAdapter connected to DataEngine")

    async def on_tick(self, tick: dict):
        """
        Receive a normalized tick from DataBridge and convert to Nautilus QuoteTick.

        Args:
            tick: Normalized tick dict with keys: symbol, ltp, bid, ask, volume, timestamp
        """
        if not NAUTILUS_AVAILABLE:
            return

        try:
            symbol = tick.get("symbol", "UNKNOWN")
            bid = tick.get("bid", 0)
            ask = tick.get("ask", 0)
            bid_qty = tick.get("bid_qty", 1)
            ask_qty = tick.get("ask_qty", 1)

            # Skip invalid ticks
            if bid <= 0 and ask <= 0:
                return

            # If only LTP is available, use it for both bid/ask
            ltp = tick.get("ltp", 0)
            if bid <= 0:
                bid = ltp
            if ask <= 0:
                ask = ltp

            # Parse timestamp
            ts_init = self._parse_timestamp_nanos(tick.get("timestamp"))

            # Create InstrumentId
            instrument_id = InstrumentId.from_str(f"{symbol}.NSE")

            # Build QuoteTick
            quote_tick = QuoteTick(
                instrument_id=instrument_id,
                bid_price=Price.from_str(f"{bid:.2f}"),
                ask_price=Price.from_str(f"{ask:.2f}"),
                bid_size=Quantity.from_int(max(bid_qty, 1)),
                ask_size=Quantity.from_int(max(ask_qty, 1)),
                ts_event=ts_init,
                ts_init=ts_init,
            )

            self._tick_count += 1

            # Push to DataEngine if connected
            if self._data_engine is not None:
                self._data_engine.process(quote_tick)

        except Exception as e:
            self._error_count += 1
            if self._error_count <= 10:  # Avoid log spam
                logger.error(f"Error converting tick for Nautilus: {e}")

    @staticmethod
    def _parse_timestamp_nanos(ts_raw) -> int:
        """Convert various timestamp formats to nanoseconds since epoch."""
        try:
            if ts_raw is None:
                return int(datetime.now().timestamp() * 1e9)
            elif isinstance(ts_raw, str):
                dt = datetime.fromisoformat(ts_raw)
                return int(dt.timestamp() * 1e9)
            elif isinstance(ts_raw, (int, float)):
                # Assume unix seconds if < 1e12, else milliseconds
                if ts_raw < 1e12:
                    return int(ts_raw * 1e9)
                else:
                    return int(ts_raw * 1e6)
            else:
                return int(datetime.now().timestamp() * 1e9)
        except (ValueError, TypeError, OSError):
            return int(datetime.now().timestamp() * 1e9)

    def get_stats(self) -> dict:
        """Get adapter statistics."""
        return {
            "ticks_converted": self._tick_count,
            "errors": self._error_count,
            "data_engine_connected": self._data_engine is not None,
        }

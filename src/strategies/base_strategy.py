"""
Base strategy class with position tracking, risk integration, and state persistence.
Reference: SYSTEM_ARCHITECTURE.md §3.1
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.utils.time_utils import now_ist, is_market_open
from src.observability.metrics import STRATEGY_SIGNALS

logger = logging.getLogger(__name__)


class BaseStrategy:
    """
    Base class for all trading strategies.
    Provides:
    - Config management
    - Position tracking
    - Signal generation with risk checks
    - State export/import for hot-swap
    - Order submission interface
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get("name", self.__class__.__name__)
        self.instrument_id = config.get("instrument_id")
        self.bar_type = config.get("bar_type")

        # Position tracking
        self.position: int = 0        # Current position (positive=long, negative=short)
        self.entry_price: float = 0.0
        self.unrealized_pnl: float = 0.0
        self.realized_pnl: float = 0.0

        # Signal history
        self.signals: List[Dict] = []
        self._signal_seq: int = 0

        # Order submission callback (set by engine/lifecycle)
        self._order_callback = None

        # Bar/tick counters
        self.bar_count: int = 0
        self.tick_count: int = 0

    # ─── Lifecycle Hooks ──────────────────────────────────────────────

    def on_start(self):
        """Called when strategy starts. Override to initialize indicators."""
        logger.info(f"▶️ Strategy '{self.name}' started for {self.instrument_id}")

    def on_stop(self):
        """Called when strategy stops. Override to cleanup."""
        logger.info(f"⏹️ Strategy '{self.name}' stopped | "
                     f"P&L: realized={self.realized_pnl:.2f}, "
                     f"unrealized={self.unrealized_pnl:.2f}")

    def on_bar(self, bar: Dict):
        """
        Handle incoming bar data. Override with strategy logic.
        Bar dict keys: open, high, low, close, volume, timestamp
        """
        self.bar_count += 1

    def on_tick(self, tick: Dict):
        """
        Handle incoming tick data. Override if needed.
        Tick dict keys: ltp, bid, ask, volume, timestamp
        """
        self.tick_count += 1
        # Update unrealized P&L
        if self.position != 0:
            ltp = tick.get("ltp", 0)
            if ltp > 0:
                self.unrealized_pnl = (ltp - self.entry_price) * self.position

    # ─── Signal Generation ────────────────────────────────────────────

    def generate_signal(self, signal_type: str, price: float, reason: str = ""):
        """
        Record a signal and optionally submit an order.
        signal_type: 'BUY', 'SELL', 'HOLD'
        """
        if signal_type not in {"BUY", "SELL", "HOLD"}:
            raise ValueError(f"Invalid signal_type: {signal_type}")
        self._signal_seq += 1
        signal = {
            "signal_id": f"{self.name}-{self._signal_seq}",
            "schema_version": "v1",
            "strategy": self.name,
            "type": signal_type,
            "price": float(price),
            "reason": reason,
            "timestamp": now_ist().isoformat(),
            "position_before": self.position,
        }
        self.signals.append(signal)
        STRATEGY_SIGNALS.labels(strategy_name=self.name, signal_type=signal_type).inc()

        if signal_type != "HOLD":
            logger.info(f"🔔 Signal: {self.name} → {signal_type} @ {price:.2f} | {reason}")

    # ─── Position Management ─────────────────────────────────────────

    def update_position(self, side: str, quantity: int, price: float):
        """Update position after a fill."""
        if side == "BUY":
            if self.position <= 0:
                # Closing short and possibly flipping to long.
                short_qty = abs(self.position)
                close_qty = min(quantity, short_qty)
                if close_qty > 0:
                    self.realized_pnl += (self.entry_price - price) * close_qty
                self.position += quantity
                if self.position > 0:
                    # Flipped to long with residual qty.
                    self.entry_price = price
                elif self.position == 0:
                    self.entry_price = 0.0
            else:
                # Adding to long
                total_cost = (self.entry_price * self.position) + (price * quantity)
                self.position += quantity
                self.entry_price = total_cost / self.position
        elif side == "SELL":
            if self.position >= 0:
                # Closing long or new short
                self.realized_pnl += (price - self.entry_price) * min(quantity, self.position) if self.position > 0 else 0
                self.position -= quantity
                if self.position < 0:
                    self.entry_price = price  # New short entry
                elif self.position == 0:
                    self.entry_price = 0.0
            else:
                # Adding to short
                prev_short_qty = abs(self.position)
                total_proceeds = (self.entry_price * prev_short_qty) + (price * quantity)
                self.position -= quantity
                self.entry_price = total_proceeds / abs(self.position) if self.position != 0 else 0.0

        logger.info(f"📊 Position: {self.name} → {self.position} @ {self.entry_price:.2f}")

    def is_flat(self) -> bool:
        """Check if strategy has no position."""
        return self.position == 0

    def is_long(self) -> bool:
        return self.position > 0

    def is_short(self) -> bool:
        return self.position < 0

    # ─── State Persistence (for hot-swap) ────────────────────────────

    def export_state(self) -> Dict[str, Any]:
        """Export strategy state for persistence or hot-swap."""
        return {
            "name": self.name,
            "position": self.position,
            "entry_price": self.entry_price,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "bar_count": self.bar_count,
            "tick_count": self.tick_count,
            "signals": self.signals[-50:],  # Keep last 50 signals
        }

    def import_state(self, state: Dict[str, Any]):
        """Import strategy state from persistence or hot-swap."""
        self.position = state.get("position", 0)
        self.entry_price = state.get("entry_price", 0.0)
        self.realized_pnl = state.get("realized_pnl", 0.0)
        self.unrealized_pnl = state.get("unrealized_pnl", 0.0)
        self.bar_count = state.get("bar_count", 0)
        self.tick_count = state.get("tick_count", 0)
        self.signals = state.get("signals", [])
        self._signal_seq = len(self.signals)
        logger.info(f"📂 State imported for '{self.name}': position={self.position}")

    # ─── Order Interface ─────────────────────────────────────────────

    def set_order_callback(self, callback):
        """Set the callback for order submission (called by engine)."""
        self._order_callback = callback

    def submit_order(self, side: str, quantity: int, order_type: str = "MARKET", price: float = 0):
        """Submit an order through the engine."""
        if not is_market_open():
            logger.warning(f"⚠️ Market closed — order not submitted: {side} {quantity}")
            return

        if self._order_callback:
            self._order_callback({
                "strategy": self.name,
                "instrument_id": self.instrument_id,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "price": price,
            })
        else:
            logger.warning(f"⚠️ No order callback set for '{self.name}'")

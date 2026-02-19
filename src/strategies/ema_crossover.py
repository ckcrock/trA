"""
EMA Crossover Strategy — uses the indicators library and base strategy infrastructure.
Reference: SYSTEM_ARCHITECTURE.md §3.1, TRADING_REFERENCE_COMPLETE.md
"""

import logging
import pandas as pd
from typing import Dict, Any
from src.strategies.base_strategy import BaseStrategy
from src.strategies.indicators import ema, rsi, atr

logger = logging.getLogger(__name__)


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy with RSI filter and ATR-based stop-loss.

    Entry:
      - BUY:  Fast EMA crosses above Slow EMA, RSI < 70  (not overbought)
      - SELL: Fast EMA crosses below Slow EMA, RSI > 30  (not oversold)

    Exit:
      - Opposite crossover or ATR-based trailing stop

    Config keys:
      - fast_period: int (default 9)
      - slow_period: int (default 21)
      - rsi_period: int (default 14)
      - atr_period: int (default 14)
      - atr_multiplier: float (default 1.5) — for stop-loss
      - quantity: int (default 1)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.fast_period = config.get("fast_period", 9)
        self.slow_period = config.get("slow_period", 21)
        self.rsi_period = config.get("rsi_period", 14)
        self.atr_period = config.get("atr_period", 14)
        self.atr_multiplier = config.get("atr_multiplier", 1.5)
        self.quantity = config.get("quantity", 1)

        # Internal state
        self.bars: list = []
        self.prev_fast_ema: float = 0.0
        self.prev_slow_ema: float = 0.0
        self.stop_loss: float = 0.0

    def on_start(self):
        super().on_start()
        logger.info(f"📐 EMA Crossover config: fast={self.fast_period}, "
                     f"slow={self.slow_period}, RSI={self.rsi_period}, "
                     f"ATR_mult={self.atr_multiplier}")

    def on_bar(self, bar: Dict):
        """Process a new bar and check for crossover signals."""
        super().on_bar(bar)
        self.bars.append(bar)

        # Need enough bars for indicators
        min_bars = max(self.slow_period, self.rsi_period, self.atr_period) + 5
        if len(self.bars) < min_bars:
            return

        # Build DataFrame from recent bars
        df = pd.DataFrame(self.bars[-200:])  # Keep last 200 bars
        close = df["close"]

        # Calculate indicators
        fast_ema = ema(close, self.fast_period)
        slow_ema = ema(close, self.slow_period)
        rsi_val = rsi(close, self.rsi_period)
        atr_val = atr(df, self.atr_period)

        current_fast = fast_ema.iloc[-1]
        current_slow = slow_ema.iloc[-1]
        prev_fast = fast_ema.iloc[-2]
        prev_slow = slow_ema.iloc[-2]
        current_rsi = rsi_val.iloc[-1]
        current_atr = atr_val.iloc[-1]
        current_price = close.iloc[-1]

        # ─── Check for crossover ─────────────────────────────────────

        # Bullish crossover: fast crosses above slow
        bullish_cross = prev_fast <= prev_slow and current_fast > current_slow
        # Bearish crossover: fast crosses below slow
        bearish_cross = prev_fast >= prev_slow and current_fast < current_slow

        # ─── Entry logic ─────────────────────────────────────────────

        if bullish_cross and current_rsi < 70 and self.is_flat():
            self.generate_signal("BUY", current_price,
                                 f"EMA bullish cross | RSI={current_rsi:.1f}")
            self.submit_order("BUY", self.quantity)
            self.stop_loss = current_price - (self.atr_multiplier * current_atr)
            logger.info(f"🎯 Stop-loss set at {self.stop_loss:.2f} "
                        f"(ATR={current_atr:.2f} × {self.atr_multiplier})")

        elif bearish_cross and current_rsi > 30 and self.is_flat():
            self.generate_signal("SELL", current_price,
                                 f"EMA bearish cross | RSI={current_rsi:.1f}")
            self.submit_order("SELL", self.quantity)
            self.stop_loss = current_price + (self.atr_multiplier * current_atr)

        # ─── Exit logic ──────────────────────────────────────────────

        elif self.is_long() and bearish_cross:
            self.generate_signal("SELL", current_price, "Exit long: bearish cross")
            self.submit_order("SELL", abs(self.position))

        elif self.is_short() and bullish_cross:
            self.generate_signal("BUY", current_price, "Exit short: bullish cross")
            self.submit_order("BUY", abs(self.position))

        # ─── Stop-loss check ─────────────────────────────────────────

        elif self.is_long() and self.stop_loss > 0 and current_price <= self.stop_loss:
            self.generate_signal("SELL", current_price,
                                 f"Stop-loss hit @ {self.stop_loss:.2f}")
            self.submit_order("SELL", abs(self.position))
            self.stop_loss = 0

        elif self.is_short() and self.stop_loss > 0 and current_price >= self.stop_loss:
            self.generate_signal("BUY", current_price,
                                 f"Stop-loss hit @ {self.stop_loss:.2f}")
            self.submit_order("BUY", abs(self.position))
            self.stop_loss = 0

        else:
            self.generate_signal("HOLD", current_price, "")

        # Update trailing stop for long positions
        if self.is_long() and self.stop_loss > 0:
            new_sl = current_price - (self.atr_multiplier * current_atr)
            if new_sl > self.stop_loss:
                self.stop_loss = new_sl

    def export_state(self) -> Dict:
        state = super().export_state()
        state.update({
            "bars_count": len(self.bars),
            "stop_loss": self.stop_loss,
            "last_bars": self.bars[-50:] if self.bars else [],
        })
        return state

    def import_state(self, state: Dict):
        super().import_state(state)
        self.stop_loss = state.get("stop_loss", 0.0)
        self.bars = state.get("last_bars", [])

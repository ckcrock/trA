"""
Circuit breaker manager — handles market-wide and stock-specific circuit breakers.
Reference: SYSTEM_ARCHITECTURE.md, MISSING_REQUIREMENTS §2.2
"""

import logging
from datetime import datetime, time
from typing import Dict, Set, Any
from src.utils.time_utils import now_ist

logger = logging.getLogger(__name__)


class CircuitBreakerManager:
    """
    Handles market-wide and stock-specific circuit breakers.
    Implements SEBI/Exchange rules for price bands and trading halts.
    """

    # Market-Wide Circuit Breakers (MWCB) — Index level
    MWCB_LEVELS = {
        "LEVEL_1": 0.10,  # 10% decline
        "LEVEL_2": 0.15,  # 15% decline
        "LEVEL_3": 0.20,  # 20% decline
    }

    # MWCB halt durations vary by time of day (SEBI rules)
    MWCB_HALT_DURATIONS = {
        "LEVEL_1": {
            "before_1pm": 45,    # 45 min halt
            "1pm_to_230pm": 15,  # 15 min halt
            "after_230pm": 0,    # No halt, but pre-close check
        },
        "LEVEL_2": {
            "before_1pm": 105,   # 1h45m halt
            "1pm_to_230pm": 45,  # 45 min halt
            "after_230pm": 0,    # Market closes for the day
        },
        "LEVEL_3": {
            "any_time": -1,      # Market closes for the day
        },
    }

    # Stock-specific price bands
    PRICE_BANDS = {
        "2_PERCENT": 0.02,    # High volatility / surveillance stocks
        "5_PERCENT": 0.05,    # Moderate liquidity stocks
        "10_PERCENT": 0.10,   # Standard stocks
        "20_PERCENT": 0.20,   # Liquid, well-traded stocks
        "NO_LIMIT": None,     # F&O stocks (derivatives eligible)
    }

    def __init__(self):
        self.mwcb_status: str = "NORMAL"
        self.mwcb_level: str = ""
        self.mwcb_triggered_at: str = ""
        self.halted_stocks: Set[str] = set()
        self.stock_limits: Dict[str, float] = {}
        self.stock_circuit_history: list = []

    def update_stock_limit(self, symbol: str, limit_percent: float):
        """Update circuit limit for a stock (loaded from daily data)."""
        self.stock_limits[symbol] = limit_percent

    def bulk_update_limits(self, limits: Dict[str, float]):
        """Bulk update stock circuit limits."""
        self.stock_limits.update(limits)

    # ─── Market-Wide Circuit Breaker ─────────────────────────────────

    def check_market_wide_circuit_breaker(
        self,
        index_name: str,
        current_level: float,
        previous_close: float,
    ) -> Dict[str, Any]:
        """
        Check if index movement triggers market-wide halt.
        Uses time-of-day dependent halt durations per SEBI rules.
        """
        if previous_close <= 0:
            return {"status": "NORMAL"}

        decline = (previous_close - current_level) / previous_close

        if decline >= self.MWCB_LEVELS["LEVEL_3"]:
            return self._trigger_mwcb("LEVEL_3", index_name, decline)

        elif decline >= self.MWCB_LEVELS["LEVEL_2"]:
            return self._trigger_mwcb("LEVEL_2", index_name, decline)

        elif decline >= self.MWCB_LEVELS["LEVEL_1"]:
            return self._trigger_mwcb("LEVEL_1", index_name, decline)

        if self.mwcb_status != "NORMAL":
            self.mwcb_status = "NORMAL"
            self.mwcb_level = ""
            logger.info("✅ MWCB status restored to NORMAL")

        return {"status": "NORMAL"}

    def _trigger_mwcb(self, level: str, index: str, decline: float) -> Dict[str, Any]:
        """Trigger a market-wide circuit breaker."""
        self.mwcb_status = "HALTED"
        self.mwcb_level = level
        self.mwcb_triggered_at = now_ist().isoformat()

        # Determine halt duration based on time of day
        halt_minutes = self._get_halt_duration(level)
        action = "CLOSE_MARKET_FOR_DAY" if halt_minutes < 0 else f"HALT_{halt_minutes}MIN"

        logger.critical(
            f"🚨 MWCB TRIGGERED: {level} on {index} | "
            f"Decline: {decline*100:.1f}% | Action: {action}"
        )

        return {
            "status": "HALTED",
            "level": level,
            "index": index,
            "decline_pct": round(decline * 100, 2),
            "action": action,
            "halt_minutes": halt_minutes,
            "triggered_at": self.mwcb_triggered_at,
        }

    def _get_halt_duration(self, level: str) -> int:
        """Get halt duration in minutes based on level and time of day."""
        now = now_ist().time()

        if level == "LEVEL_3":
            return -1  # Close for day

        durations = self.MWCB_HALT_DURATIONS.get(level, {})

        if now < time(13, 0):
            return durations.get("before_1pm", 45)
        elif now < time(14, 30):
            return durations.get("1pm_to_230pm", 15)
        else:
            result = durations.get("after_230pm", 0)
            if level == "LEVEL_2":
                return -1  # Close for day after 2:30
            return result

    # ─── Stock-Specific Circuit Limits ───────────────────────────────

    def check_stock_circuit_limit(
        self,
        symbol: str,
        current_price: float,
        previous_close: float,
    ) -> Dict[str, Any]:
        """Check if stock hits circuit limit."""
        limit = self.stock_limits.get(symbol, self.PRICE_BANDS["10_PERCENT"])

        if limit is None:
            return {"status": "NORMAL", "reason": "NO_LIMIT (F&O eligible)"}

        if previous_close <= 0:
            return {"status": "NORMAL"}

        change = (current_price - previous_close) / previous_close

        if change >= limit:
            self.halted_stocks.add(symbol)
            result = {
                "status": "UPPER_CIRCUIT",
                "symbol": symbol,
                "change_pct": round(change * 100, 2),
                "limit_price": round(previous_close * (1 + limit), 2),
                "is_halted": True,
            }
            self.stock_circuit_history.append({**result, "timestamp": now_ist().isoformat()})
            logger.warning(f"⬆️ UPPER CIRCUIT: {symbol} @ {change*100:.1f}%")
            return result

        elif change <= -limit:
            self.halted_stocks.add(symbol)
            result = {
                "status": "LOWER_CIRCUIT",
                "symbol": symbol,
                "change_pct": round(change * 100, 2),
                "limit_price": round(previous_close * (1 - limit), 2),
                "is_halted": True,
            }
            self.stock_circuit_history.append({**result, "timestamp": now_ist().isoformat()})
            logger.warning(f"⬇️ LOWER CIRCUIT: {symbol} @ {change*100:.1f}%")
            return result

        # Remove from halted if recovered
        self.halted_stocks.discard(symbol)
        return {"status": "NORMAL"}

    # ─── Execution Gate ──────────────────────────────────────────────

    def is_execution_allowed(self, symbol: str, side: str = None) -> bool:
        """Check if execution is allowed for this symbol."""
        if self.mwcb_status != "NORMAL":
            return False
        if symbol in self.halted_stocks:
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status summary."""
        return {
            "mwcb_status": self.mwcb_status,
            "mwcb_level": self.mwcb_level,
            "halted_stocks": list(self.halted_stocks),
            "halted_count": len(self.halted_stocks),
            "recent_circuits": self.stock_circuit_history[-10:],
        }

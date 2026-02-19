"""
Market session manager — handles pre-open, regular, post-market sessions
and auto square-off for MIS positions.
Reference: MISSING_REQUIREMENTS §5.1, §2.4
"""

import logging
import asyncio
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime
from src.utils.time_utils import (
    now_ist, get_market_session, is_market_open,
    should_square_off_mis, is_trading_day,
    time_to_market_open, time_to_market_close,
    MIS_SQUARE_OFF, MARKET_OPEN, MARKET_CLOSE
)

logger = logging.getLogger(__name__)


class MarketSessionManager:
    """
    Manages market session transitions and MIS auto square-off.

    Sessions (IST):
      PRE_OPEN:    09:00 - 09:15
      REGULAR:     09:15 - 15:30
      POST_MARKET: 15:30 - 16:00
      CLOSED:      16:00 - 09:00 (next day)

    Auto Square-Off:
      MIS positions are closed at 15:15 IST (before market close).
    """

    def __init__(self):
        self.current_session: str = "CLOSED"
        self.running: bool = False
        self._task: Optional[asyncio.Task] = None

        # Callbacks for session transitions
        self._on_session_change: List[Callable] = []
        self._on_square_off: List[Callable] = []

        # Tracking
        self.session_transitions: List[Dict] = []
        self.square_off_triggered: bool = False

    def on_session_change(self, callback: Callable):
        """Register callback for session transitions. Called with (old_session, new_session)."""
        self._on_session_change.append(callback)

    def on_square_off(self, callback: Callable):
        """Register callback for MIS auto square-off trigger. Called with no args."""
        self._on_square_off.append(callback)

    async def start(self):
        """Start the session monitor loop."""
        self.running = True
        self.current_session = get_market_session()
        self.square_off_triggered = False
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"✅ Market session manager started (session={self.current_session})")

    async def stop(self):
        """Stop the session monitor."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("⏹️ Market session manager stopped")

    async def _monitor_loop(self):
        """Monitor market session every 5 seconds."""
        while self.running:
            try:
                new_session = get_market_session()

                # Session transition
                if new_session != self.current_session:
                    old_session = self.current_session
                    self.current_session = new_session

                    self.session_transitions.append({
                        "from": old_session,
                        "to": new_session,
                        "timestamp": now_ist().isoformat(),
                    })

                    logger.info(f"🔔 Session change: {old_session} → {new_session}")

                    # Reset daily square_off flag on new day
                    if new_session == "PRE_OPEN":
                        self.square_off_triggered = False

                    # Notify callbacks
                    for cb in self._on_session_change:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                await cb(old_session, new_session)
                            else:
                                cb(old_session, new_session)
                        except Exception as e:
                            logger.error(f"❌ Session change callback error: {e}")

                # MIS auto square-off check
                if (
                    self.current_session == "REGULAR"
                    and should_square_off_mis()
                    and not self.square_off_triggered
                ):
                    self.square_off_triggered = True
                    logger.warning("⚠️ MIS AUTO SQUARE-OFF TRIGGERED (15:15 IST)")

                    for cb in self._on_square_off:
                        try:
                            if asyncio.iscoroutinefunction(cb):
                                await cb()
                            else:
                                cb()
                        except Exception as e:
                            logger.error(f"❌ Square-off callback error: {e}")

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Session monitor error: {e}")
                await asyncio.sleep(5)

    def get_status(self) -> Dict[str, Any]:
        """Get current session status."""
        ttc = time_to_market_close()
        tto = time_to_market_open()

        return {
            "session": self.current_session,
            "is_market_open": is_market_open(),
            "is_trading_day": is_trading_day(),
            "square_off_triggered": self.square_off_triggered,
            "time_to_close": str(ttc) if ttc else None,
            "time_to_open": str(tto) if tto else None,
            "transitions_today": len(self.session_transitions),
        }

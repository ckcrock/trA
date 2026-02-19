"""
Background workers for periodic tasks.
Reference: SYSTEM_ARCHITECTURE.md Section 3.2
"""

import asyncio
import logging
import random
from src.utils.time_utils import is_market_open

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages periodic background tasks:
    - Session refresh (every 5 min)
    - Position sync (every 60s during market hours)
    - Health check (every 10s)
    """

    def __init__(self, auth_manager=None, execution_client=None, health_checker=None):
        self.auth = auth_manager
        self.execution = execution_client
        self.health = health_checker
        self.running = False
        self._tasks = []

    @staticmethod
    def _jitter(seconds: float, pct: float = 0.05) -> float:
        """Return a small randomized delay to avoid synchronized bursts."""
        delta = seconds * pct
        return max(0.0, seconds + random.uniform(-delta, delta))

    async def start(self):
        """Start all background tasks."""
        self.running = True
        self._tasks = [
            asyncio.create_task(self._session_refresh_loop(), name="bg-session-refresh"),
            asyncio.create_task(self._health_check_loop(), name="bg-health-check"),
            asyncio.create_task(self._position_sync_loop(), name="bg-position-sync"),
        ]
        logger.info("Background tasks started (%s workers)", len(self._tasks))

    async def stop(self):
        """Stop all background tasks."""
        self.running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Background tasks stopped")

    async def _session_refresh_loop(self):
        """Refresh broker session every 5 minutes."""
        while self.running:
            try:
                if self.auth:
                    self.auth.ensure_authenticated()
                    if self.health:
                        self.health.update_component("broker_auth", "healthy")
                    logger.debug("Session refreshed")
                await asyncio.sleep(self._jitter(300))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Session refresh error: %s", e)
                if self.health:
                    self.health.update_component("broker_auth", "unhealthy", {"error": str(e)})
                await asyncio.sleep(self._jitter(60))

    async def _health_check_loop(self):
        """Update API server health heartbeat every 10 seconds."""
        while self.running:
            try:
                if self.health:
                    self.health.update_component("api_server", "healthy")
                await asyncio.sleep(self._jitter(10))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error: %s", e)
                await asyncio.sleep(self._jitter(10))

    async def _position_sync_loop(self):
        """Sync positions with broker every 60 seconds during market hours."""
        while self.running:
            try:
                if is_market_open() and self.execution:
                    try:
                        positions = await self.execution.get_positions()
                        net_positions = positions.get("net", []) if isinstance(positions, dict) else []
                        if self.health:
                            self.health.update_component(
                                "position_sync",
                                "healthy",
                                {"net_positions": len(net_positions)},
                            )
                        logger.debug("Positions synced: %s net positions", len(net_positions))
                    except Exception as e:
                        logger.error("Position sync error: %s", e)
                        if self.health:
                            self.health.update_component("position_sync", "degraded", {"error": str(e)})
                await asyncio.sleep(self._jitter(60))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Position sync loop error: %s", e)
                await asyncio.sleep(self._jitter(60))

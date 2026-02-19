"""
Background workers for periodic tasks.
Reference: SYSTEM_ARCHITECTURE.md §3.2
"""

import logging
import asyncio
from typing import Optional
from src.utils.time_utils import now_ist, is_market_open

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages periodic background tasks:
    - Session refresh (every 5 min)
    - Position sync (every 60s during market hours)
    - Health check (every 10s)
    - Order reconciliation (every 30s during market hours)
    """

    def __init__(self, auth_manager=None, execution_client=None, health_checker=None):
        self.auth = auth_manager
        self.execution = execution_client
        self.health = health_checker
        self.running = False
        self._tasks = []

    async def start(self):
        """Start all background tasks."""
        self.running = True
        self._tasks = [
            asyncio.create_task(self._session_refresh_loop()),
            asyncio.create_task(self._health_check_loop()),
            asyncio.create_task(self._position_sync_loop()),
        ]
        logger.info(f"✅ Background tasks started ({len(self._tasks)} workers)")

    async def stop(self):
        """Stop all background tasks."""
        self.running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("⏹️ Background tasks stopped")

    async def _session_refresh_loop(self):
        """Refresh broker session every 5 minutes."""
        while self.running:
            try:
                if self.auth:
                    self.auth.ensure_authenticated()
                    if self.health:
                        self.health.update_component("broker_auth", "healthy")
                    logger.debug("🔄 Session refreshed")
                await asyncio.sleep(300)  # 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Session refresh error: {e}")
                if self.health:
                    self.health.update_component("broker_auth", "unhealthy", {"error": str(e)})
                await asyncio.sleep(60)

    async def _health_check_loop(self):
        """Update health status every 10 seconds."""
        while self.running:
            try:
                if self.health:
                    # Update API server status
                    self.health.update_component("api_server", "healthy")
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
                await asyncio.sleep(10)

    async def _position_sync_loop(self):
        """Sync positions with broker every 60 seconds during market hours."""
        while self.running:
            try:
                if is_market_open() and self.execution:
                    try:
                        positions = await self.execution.get_positions()
                        logger.debug(f"📊 Positions synced: {len(positions.get('data', {}).get('net', []))} net positions")
                    except Exception as e:
                        logger.error(f"❌ Position sync error: {e}")
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Position sync loop error: {e}")
                await asyncio.sleep(60)

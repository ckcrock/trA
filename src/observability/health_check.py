"""
Health check endpoint and system status.
Reference: SYSTEM_ARCHITECTURE.md §3.7
"""

import logging
import time
import psutil
from typing import Dict, Any
from datetime import datetime
from src.utils.time_utils import now_ist, get_market_session

logger = logging.getLogger(__name__)

# Track startup time
_startup_time = time.time()


class HealthChecker:
    """
    Aggregates health status from all system components.
    """

    def __init__(self):
        self.components: Dict[str, Dict[str, Any]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register default component health entries."""
        self.components = {
            "broker_auth": {"status": "unknown", "last_check": None},
            "broker_websocket": {"status": "unknown", "last_check": None},
            "data_bridge": {"status": "unknown", "queue_size": 0, "last_check": None},
            "api_server": {"status": "healthy", "last_check": now_ist().isoformat()},
        }

    def update_component(self, name: str, status: str, details: Dict = None):
        """Update the health status of a component."""
        entry = {
            "status": status,
            "last_check": now_ist().isoformat(),
        }
        if details:
            entry.update(details)
        self.components[name] = entry

    def get_health(self) -> Dict[str, Any]:
        """Get full system health report."""
        # System metrics
        process = psutil.Process()
        memory = process.memory_info()

        # Overall status: healthy if all known components are healthy/unknown
        statuses = [c.get("status", "unknown") for c in self.components.values()]
        overall = "healthy"
        if "unhealthy" in statuses:
            overall = "unhealthy"
        elif "degraded" in statuses:
            overall = "degraded"

        return {
            "status": overall,
            "timestamp": now_ist().isoformat(),
            "uptime_seconds": round(time.time() - _startup_time, 1),
            "market_session": get_market_session(),
            "system": {
                "memory_mb": round(memory.rss / 1024 / 1024, 1),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "threads": process.num_threads(),
            },
            "components": self.components,
        }

    def is_healthy(self) -> bool:
        """Quick check — is the system overall healthy?"""
        health = self.get_health()
        return health["status"] == "healthy"


# ─── Global Instance ─────────────────────────────────────────────────
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get or create the singleton HealthChecker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker

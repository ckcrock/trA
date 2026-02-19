"""
Strategy lifecycle manager.
Handles start/stop/pause, hot-swap, state serialization.
Reference: SYSTEM_ARCHITECTURE.md §3.1
"""

import logging
import json
import os
import time
from typing import Dict, Any, Optional, Type
from datetime import datetime
from src.utils.time_utils import now_ist
from src.observability.metrics import ACTIVE_STRATEGIES

logger = logging.getLogger(__name__)


class StrategyLifecycleManager:
    """
    Manages the lifecycle of trading strategies:
    - Registration, start, stop, pause, resume
    - Hot-swap (replace strategy while preserving state)
    - State persistence to disk
    """

    STATE_DIR = "data/strategy_state"

    def __init__(self):
        self.strategies: Dict[str, Dict[str, Any]] = {}
        os.makedirs(self.STATE_DIR, exist_ok=True)

    def register(self, name: str, strategy_instance: Any, config: Dict = None) -> bool:
        """Register a strategy instance."""
        if name in self.strategies:
            logger.warning(f"⚠️ Strategy '{name}' already registered")
            return False

        self.strategies[name] = {
            "instance": strategy_instance,
            "config": config or {},
            "status": "REGISTERED",
            "started_at": None,
            "stopped_at": None,
            "signal_count": 0,
        }
        logger.info(f"✅ Strategy '{name}' registered")
        return True

    def start(self, name: str) -> bool:
        """Start a registered strategy."""
        entry = self.strategies.get(name)
        if not entry:
            logger.error(f"❌ Strategy '{name}' not found")
            return False

        if entry["status"] == "RUNNING":
            logger.warning(f"⚠️ Strategy '{name}' is already running")
            return False

        # Restore state if available
        self._restore_state(name)

        # Call strategy's on_start
        strategy = entry["instance"]
        if hasattr(strategy, "on_start"):
            strategy.on_start()

        entry["status"] = "RUNNING"
        entry["started_at"] = now_ist().isoformat()
        ACTIVE_STRATEGIES.inc()
        logger.info(f"▶️ Strategy '{name}' started")
        return True

    def stop(self, name: str) -> bool:
        """Stop a running strategy."""
        entry = self.strategies.get(name)
        if not entry:
            logger.error(f"❌ Strategy '{name}' not found")
            return False

        if entry["status"] != "RUNNING":
            logger.warning(f"⚠️ Strategy '{name}' is not running (status: {entry['status']})")
            return False

        # Save state before stopping
        self._save_state(name)

        # Call strategy's on_stop
        strategy = entry["instance"]
        if hasattr(strategy, "on_stop"):
            strategy.on_stop()

        entry["status"] = "STOPPED"
        entry["stopped_at"] = now_ist().isoformat()
        ACTIVE_STRATEGIES.dec()
        logger.info(f"⏹️ Strategy '{name}' stopped")
        return True

    def pause(self, name: str) -> bool:
        """Pause a running strategy (stops receiving new signals but keeps state)."""
        entry = self.strategies.get(name)
        if not entry or entry["status"] != "RUNNING":
            return False
        entry["status"] = "PAUSED"
        logger.info(f"⏸️ Strategy '{name}' paused")
        return True

    def resume(self, name: str) -> bool:
        """Resume a paused strategy."""
        entry = self.strategies.get(name)
        if not entry or entry["status"] != "PAUSED":
            return False
        entry["status"] = "RUNNING"
        logger.info(f"▶️ Strategy '{name}' resumed")
        return True

    def hot_swap(self, name: str, new_strategy_instance: Any, new_config: Dict = None) -> bool:
        """
        Replace a running strategy with a new instance.
        1. Pause old strategy
        2. Export state
        3. Import state to new strategy
        4. Switch
        """
        entry = self.strategies.get(name)
        if not entry:
            logger.error(f"❌ Strategy '{name}' not found for hot-swap")
            return False

        old_instance = entry["instance"]
        old_status = entry["status"]

        logger.info(f"🔄 Hot-swapping strategy '{name}'...")

        # 1. Pause old
        if old_status == "RUNNING":
            self.pause(name)

        # 2. Export state from old
        state = {}
        if hasattr(old_instance, "export_state"):
            state = old_instance.export_state()

        # 3. Import state to new
        if hasattr(new_strategy_instance, "import_state"):
            new_strategy_instance.import_state(state)

        # 4. Stop old, register new
        if hasattr(old_instance, "on_stop"):
            old_instance.on_stop()

        entry["instance"] = new_strategy_instance
        entry["config"] = new_config or entry["config"]
        entry["status"] = "REGISTERED"

        # 5. Start new if old was running
        if old_status == "RUNNING":
            self.start(name)

        logger.info(f"✅ Strategy '{name}' hot-swapped successfully")
        return True

    def get_status(self, name: str = None) -> Dict:
        """Get status of one or all strategies."""
        if name:
            entry = self.strategies.get(name)
            if not entry:
                return {}
            return {
                "name": name,
                "status": entry["status"],
                "started_at": entry["started_at"],
                "stopped_at": entry["stopped_at"],
                "signal_count": entry["signal_count"],
            }

        return {
            n: {
                "status": e["status"],
                "started_at": e["started_at"],
                "signal_count": e["signal_count"],
            }
            for n, e in self.strategies.items()
        }

    def is_running(self, name: str) -> bool:
        """Check if a strategy is running."""
        entry = self.strategies.get(name)
        return entry is not None and entry["status"] == "RUNNING"

    def _save_state(self, name: str):
        """Persist strategy state to disk."""
        entry = self.strategies.get(name)
        if not entry:
            return

        strategy = entry["instance"]
        state = {}
        if hasattr(strategy, "export_state"):
            state = strategy.export_state()

        path = os.path.join(self.STATE_DIR, f"{name}_state.json")
        try:
            with open(path, "w") as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"💾 State saved for '{name}' → {path}")
        except Exception as e:
            logger.error(f"❌ Failed to save state for '{name}': {e}")

    def _restore_state(self, name: str):
        """Restore strategy state from disk."""
        path = os.path.join(self.STATE_DIR, f"{name}_state.json")
        if not os.path.exists(path):
            return

        entry = self.strategies.get(name)
        if not entry:
            return

        try:
            with open(path, "r") as f:
                state = json.load(f)
            strategy = entry["instance"]
            if hasattr(strategy, "import_state"):
                strategy.import_state(state)
            logger.info(f"📂 State restored for '{name}' from {path}")
        except Exception as e:
            logger.error(f"❌ Failed to restore state for '{name}': {e}")

    def unregister(self, name: str) -> bool:
        """Unregister a strategy (must be stopped first)."""
        entry = self.strategies.get(name)
        if not entry:
            return False
        if entry["status"] == "RUNNING":
            self.stop(name)
        del self.strategies[name]
        logger.info(f"🗑️ Strategy '{name}' unregistered")
        return True

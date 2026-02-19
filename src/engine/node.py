"""
Trading Node wrapper â€” manages configuration, lifecycle, and strategy orchestration.
Reference: SYSTEM_ARCHITECTURE.md Â§3.1
"""

import logging
import asyncio
from typing import Dict, Any, Optional

from src.engine.config_loader import load_trading_node_config, load_risk_limits
from src.engine.lifecycle import StrategyLifecycleManager
from src.adapters.nautilus import NAUTILUS_AVAILABLE

if NAUTILUS_AVAILABLE:
    try:
        from nautilus_trader.model.identifiers import TraderId
    except ImportError:
        NAUTILUS_AVAILABLE = False


logger = logging.getLogger(__name__)


class TradingNodeWrapper:
    """
    Wrapper around Nautilus Trader's TradingNode.
    Manages configuration, lifecycle, and strategy registration.

    When Nautilus is not installed, operates as a standalone orchestrator
    using the StrategyLifecycleManager for strategy management.
    """

    def __init__(self, config_path: str = "config/trading_node.yaml"):
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.risk_limits: Dict[str, Any] = {}
        self.node = None  # NautilusNode when available
        self.lifecycle = StrategyLifecycleManager()
        self.running = False

    def load_config(self):
        """Load trading node and risk configuration from YAML."""
        try:
            self.config = load_trading_node_config(self.config_path)
            self.risk_limits = load_risk_limits()
            logger.info(f"âœ… Trading node config loaded: trader_id={self.config.get('trader_id')}")
        except FileNotFoundError as e:
            logger.warning(f"âš ï¸ Config not found, using defaults: {e}")
            self.config = {"trader_id": "TRADER-001", "instance_id": "001"}
            self.risk_limits = {}

    async def start(self):
        """Start the trading node."""
        logger.info("ðŸš€ Starting Trading Node...")

        # Load configuration
        self.load_config()

        # Start Nautilus TradingNode if available
        if NAUTILUS_AVAILABLE:
            try:
                from nautilus_trader.live.node import TradingNode as NautilusNode

                from nautilus_trader.config import TradingNodeConfig
                from src.adapters.nautilus.factories import AngelOneDataClientFactory, AngelOneExecClientFactory
                from src.adapters.nautilus.config import AngelOneDataClientConfig, AngelOneExecClientConfig
                
                trader_id_val = self.config.get("trader_id", "TRADER-001")
                if "-" not in trader_id_val:
                    trader_id_val = f"{trader_id_val}-001"
                
                config_kwargs = {"trader_id": TraderId(trader_id_val)}
                if "instance_id" in getattr(TradingNodeConfig, "__annotations__", {}):
                    config_kwargs["instance_id"] = self.config.get("instance_id", "001")
                nautilus_config = TradingNodeConfig(**config_kwargs)
                self.node = NautilusNode(config=nautilus_config)
                
                # Register Angel One factories with API-compat fallback.
                if hasattr(self.node, "register_data_client_factory"):
                    self.node.register_data_client_factory(
                        "ANGELONE",
                        AngelOneDataClientFactory,
                        valid_config_types=[AngelOneDataClientConfig],
                    )
                elif hasattr(self.node, "add_data_client_factory"):
                    self.node.add_data_client_factory("ANGELONE", AngelOneDataClientFactory)

                if hasattr(self.node, "register_exec_client_factory"):
                    self.node.register_exec_client_factory(
                        "ANGELONE",
                        AngelOneExecClientFactory,
                        valid_config_types=[AngelOneExecClientConfig],
                    )
                elif hasattr(self.node, "add_exec_client_factory"):
                    self.node.add_exec_client_factory("ANGELONE", AngelOneExecClientFactory)
                
                logger.info(f"âœ… Nautilus TradingNode initialized (Trader ID: {trader_id_val})")
                
                # Note: We do NOT await self.node.run_async() here as it blocks.
                # In a real system, we might run it in a separate task or rely on the main loop.
                # For now, initialization is enough to register factories.
                
            except Exception as e:
                logger.error(f"Failed to initialize Nautilus Node: {e}")

        self.running = True
        logger.info(f"âœ… Trading Node started (trader_id={self.config.get('trader_id')})")

    async def stop(self):
        """Stop the trading node and all strategies."""
        logger.info("â¹ï¸ Stopping Trading Node...")

        # Stop all strategies
        for name in list(self.lifecycle.strategies.keys()):
            if self.lifecycle.is_running(name):
                self.lifecycle.stop(name)

        # Stop Nautilus node
        if self.node:
             self.node.stop()

        self.running = False
        logger.info("âœ… Trading Node stopped")

    def add_strategy(self, name: str, strategy_instance: Any, config: Dict = None):
        """Register and optionally start a strategy."""
        self.lifecycle.register(name, strategy_instance, config)

        # Also register with Nautilus if available
        if self.node and hasattr(strategy_instance, "config"):
             # self.node.trader.add_strategy(strategy_instance)
             pass

        logger.info(f"ðŸ“‹ Strategy '{name}' added to trading node")

    def start_strategy(self, name: str) -> bool:
        """Start a registered strategy."""
        return self.lifecycle.start(name)

    def stop_strategy(self, name: str) -> bool:
        """Stop a running strategy."""
        return self.lifecycle.stop(name)

    def get_strategy_status(self, name: str = None) -> Dict:
        """Get status of strategies."""
        return self.lifecycle.get_status(name)

    def is_running(self) -> bool:
        """Check if the trading node is running."""
        return self.running



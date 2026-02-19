"""
YAML configuration loader for trading node and strategies.
Reference: SYSTEM_ARCHITECTURE.md §3.1
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML config file. Raises FileNotFoundError if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}
    logger.info(f"✅ Loaded config: {path}")
    return data


def load_trading_node_config(
    path: str = "config/trading_node.yaml",
) -> Dict[str, Any]:
    """Load trading node configuration."""
    config = load_yaml(path)
    # Support both flat schema and nested schema under `node:`.
    if "node" in config and isinstance(config["node"], dict):
        config = config["node"]
    # Merge with defaults
    defaults = {
        "trader_id": "TRADER-001",
        "instance_id": "001",
        "log_level": "INFO",
        "timeout_connection": 30,
        "timeout_reconciliation": 10,
        "timeout_portfolio": 10,
    }
    merged = {**defaults, **config}
    return merged


def load_risk_limits(
    path: str = "config/risk_limits.yaml",
) -> Dict[str, Any]:
    """Load risk management limits."""
    config = load_yaml(path)
    # Provide safe defaults if keys missing
    defaults = {
        "position_limits": {
            "max_position_pct": 0.10,
            "max_daily_loss_pct": 0.03,
            "max_open_positions": 10,
            "max_order_value": 500000,
        },
        "rate_limits": {
            "ops_threshold": 10,
            "historical_rpm": 3,
            "order_rpm": 10,
        },
    }
    for section, section_defaults in defaults.items():
        if section not in config:
            config[section] = section_defaults
        else:
            for key, value in section_defaults.items():
                config[section].setdefault(key, value)
    return config


def load_strategy_config(strategy_name: str) -> Optional[Dict[str, Any]]:
    """
    Load strategy-specific configuration.
    Looks in config/strategies/<strategy_name>.yaml
    """
    path = f"config/strategies/{strategy_name}.yaml"
    if not os.path.exists(path):
        logger.warning(f"⚠️ No config found for strategy '{strategy_name}' at {path}")
        return None
    return load_yaml(path)

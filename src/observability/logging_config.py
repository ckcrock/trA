"""
Structured logging configuration.
Loads from config/logging.yaml and sets up handlers.
Reference: SYSTEM_ARCHITECTURE.md Section 3.7
"""

import logging
import logging.config
import os

import yaml


def setup_logging(config_path: str = "config/logging.yaml", default_level: int = logging.INFO):
    """
    Initialize logging from YAML config.
    Falls back to basic config if YAML is unavailable.
    """
    os.makedirs("data/logs", exist_ok=True)

    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
        logging.getLogger(__name__).info(f"Logging configured from {config_path}")
    else:
        logging.basicConfig(
            level=default_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger(__name__).warning(
            f"Logging config not found at {config_path}, using basic config"
        )

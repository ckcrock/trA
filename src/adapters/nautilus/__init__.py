"""
NautilusTrader adapter for Angel One.
Wraps existing adapters to provide Nautilus-compatible interfaces.
"""

import logging

try:
    import nautilus_trader
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

logger = logging.getLogger(__name__)

if not NAUTILUS_AVAILABLE:
    logger.warning("NautilusTrader not installed. Adapter features will be disabled.")

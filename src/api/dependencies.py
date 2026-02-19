import os
from dotenv import load_dotenv

from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter
from src.adapters.angel.data_client import AngelDataClient
from src.adapters.angel.websocket_client import AngelWebSocketClient
from src.adapters.angel.execution_client import AngelExecutionClient
from src.bridge.data_bridge import DataBridge
from src.catalog.symbol_resolver import SymbolResolver
from src.observability.health_check import HealthChecker, get_health_checker as _get_hc
from src.engine.lifecycle import StrategyLifecycleManager
from src.engine.node import TradingNodeWrapper

load_dotenv()

# Global Instances (Singletons)
_auth_manager = None
_rate_limiter = None
_data_client = None
_ws_client = None
_exec_client = None
_data_bridge = None
_symbol_resolver = None
_trading_node = None


def get_auth_manager() -> AngelAuthManager:
    global _auth_manager
    if not _auth_manager:
        _auth_manager = AngelAuthManager(
            api_key=os.getenv("ANGEL_API_KEY"),
            client_code=os.getenv("ANGEL_CLIENT_CODE"),
            mpin=os.getenv("ANGEL_PASSWORD"),
            totp_secret=os.getenv("ANGEL_TOTP_SECRET"),
            hist_api_key=os.getenv("ANGEL_HIST_API_KEY")
        )
    return _auth_manager


def get_rate_limiter() -> TokenBucketRateLimiter:
    global _rate_limiter
    if not _rate_limiter:
        _rate_limiter = TokenBucketRateLimiter(rate=3.0)  # Conservative limit
    return _rate_limiter


def get_data_client() -> AngelDataClient:
    global _data_client
    if not _data_client:
        _data_client = AngelDataClient(get_auth_manager(), get_rate_limiter())
    return _data_client


def get_ws_client() -> AngelWebSocketClient:
    global _ws_client
    if not _ws_client:
        _ws_client = AngelWebSocketClient(get_auth_manager())
    return _ws_client


def get_execution_client() -> AngelExecutionClient:
    global _exec_client
    if not _exec_client:
        _exec_client = AngelExecutionClient(get_auth_manager(), get_rate_limiter())
    return _exec_client


def get_data_bridge() -> DataBridge:
    global _data_bridge
    if not _data_bridge:
        _data_bridge = DataBridge()
    return _data_bridge


def get_symbol_resolver() -> SymbolResolver:
    global _symbol_resolver
    if not _symbol_resolver:
        _symbol_resolver = SymbolResolver()
    return _symbol_resolver


def get_health_checker() -> HealthChecker:
    return _get_hc()


def get_trading_node() -> TradingNodeWrapper:
    global _trading_node
    if not _trading_node:
        _trading_node = TradingNodeWrapper()
    return _trading_node


def get_lifecycle_manager() -> StrategyLifecycleManager:
    """Delegate to Trading Node's lifecycle manager."""
    return get_trading_node().lifecycle

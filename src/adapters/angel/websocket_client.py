import logging
from typing import Dict, List, Callable, Optional, Any

from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from src.adapters.angel.auth import AngelAuthManager
from src.observability.health_check import get_health_checker

try:
    from src.observability.metrics import WS_CONNECTIONS, WS_RECONNECTS, WS_SUBSCRIBE_ERRORS
    METRICS_AVAILABLE = True
except Exception:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)


class AngelWebSocketClient:
    """
    WebSocket client for live market data streaming.
    Wraps SmartWebSocketV2 with reconnect-safe subscription handling.
    """

    EXCHANGE_TYPE_MAP = {
        "NSE": 1,
        "NSE_CM": 1,
        "NFO": 2,
        "NSE_FO": 2,
        "BSE": 3,
        "BSE_CM": 3,
        "BSE_FO": 4,
        "MCX": 5,
        "MCX_FO": 5,
        "NCX_FO": 7,
        "CDE_FO": 13,
    }

    def __init__(self, auth_manager: AngelAuthManager):
        self.auth = auth_manager
        self.sws: Optional[SmartWebSocketV2] = None
        self.is_connected = False
        self._ever_connected = False
        self.callbacks: List[Callable] = []
        self.subscribed_tokens: Dict[int, List[Dict[str, Any]]] = {}

    def _on_data(self, ws, message):
        """Internal callback for raw data."""
        for callback in self.callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}")

    def _on_open(self, ws):
        logger.info("WebSocket connection opened")
        self.is_connected = True
        if METRICS_AVAILABLE:
            WS_CONNECTIONS.labels(type="broker").set(1)
            if self._ever_connected:
                WS_RECONNECTS.inc()
        self._ever_connected = True
        get_health_checker().update_component("broker_websocket", "healthy")

        # Restore subscriptions after reconnect.
        for mode, token_groups in self.subscribed_tokens.items():
            if not token_groups:
                continue
            try:
                self.sws.subscribe("reconnect01", mode, token_groups)
            except Exception as e:
                logger.error(f"Resubscribe failed for mode {mode}: {e}")

    def _on_close(self, ws, *args):
        logger.warning("WebSocket connection closed")
        self.is_connected = False
        if METRICS_AVAILABLE:
            WS_CONNECTIONS.labels(type="broker").set(0)
        get_health_checker().update_component("broker_websocket", "degraded")

    def _on_error(self, ws, error=None, *args):
        logger.error(f"WebSocket error: {error}")
        get_health_checker().update_component("broker_websocket", "unhealthy", {"error": str(error)})

    def _init_sws(self):
        """Initialize the SmartWebSocketV2 instance if not already done."""
        if self.sws:
            return

        self.auth.ensure_authenticated()
        self.sws = SmartWebSocketV2(
            auth_token=self.auth.access_token,
            api_key=self.auth.api_key,
            client_code=self.auth.client_code,
            feed_token=self.auth.feed_token,
            max_retry_attempt=3,
        )

        # Monkey-patch SDK bug in _on_close arity handling.
        orig_on_close = self.sws._on_close

        def patched_on_close(ws, *args):
            try:
                if len(args) == 2:
                    return orig_on_close(ws, args[0], args[1])
                return orig_on_close(ws, *args[:2] if len(args) > 2 else args)
            except Exception:
                return None

        self.sws._on_close = patched_on_close

        # Assign callbacks
        self.sws.on_open = self._on_open
        self.sws.on_data = self._on_data
        self.sws.on_error = self._on_error
        self.sws.on_close = self._on_close

    def connect(self):
        """Initialize and connect WebSocket (blocking)."""
        self._init_sws()
        self.sws.connect()

    def connect_in_thread(self):
        """Connect WebSocket in a separate thread (non-blocking)."""
        self._init_sws()
        import threading

        thread = threading.Thread(target=self.connect, daemon=True)
        thread.start()
        return thread

    def subscribe(self, mode: int, token_list: List[Dict[str, Any]]):
        """Subscribe to tokens using SmartWebSocketV2 payload format."""
        if not self.sws:
            logger.warning("WebSocket not initialized. Attempting to connect...")
            self.connect()

        import time

        wait_start = time.time()
        while not self.is_connected and time.time() - wait_start < 5:
            time.sleep(0.5)

        if not self.is_connected:
            logger.error("WebSocket not connected after waiting. Subscription may fail.")

        try:
            normalized_tokens = self._normalize_token_list(token_list)
            correlation_id = "abcde12345"
            self.sws.subscribe(correlation_id, mode, normalized_tokens)
            self.subscribed_tokens[mode] = normalized_tokens
            logger.info(f"Subscribed to {len(normalized_tokens)} token groups in mode {mode}")
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            if METRICS_AVAILABLE:
                WS_SUBSCRIBE_ERRORS.inc()

    def _normalize_token_list(self, token_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize token list to SmartWebSocketV2 format:
        [{"exchangeType": int, "tokens": [str, ...]}, ...]
        """
        normalized: List[Dict[str, Any]] = []

        for item in token_list:
            exch = item.get("exchangeType")
            if isinstance(exch, str):
                exch = self.EXCHANGE_TYPE_MAP.get(exch.strip().upper())
            if not isinstance(exch, int):
                raise ValueError(f"Invalid exchangeType: {item.get('exchangeType')}")

            raw_tokens = item.get("tokens", [])
            if not isinstance(raw_tokens, list) or not raw_tokens:
                raise ValueError("Each token group must include non-empty 'tokens' list")

            normalized.append({
                "exchangeType": exch,
                "tokens": [str(token) for token in raw_tokens],
            })

        return normalized

    def register_callback(self, callback: Callable):
        """Register a function to be called on new ticks."""
        self.callbacks.append(callback)

    def close(self):
        if self.sws:
            self.sws.close_connection()

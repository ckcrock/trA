import logging
import asyncio
from typing import Dict, List, Callable, Optional
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from src.adapters.angel.auth import AngelAuthManager

logger = logging.getLogger(__name__)

class AngelWebSocketClient:
    """
    WebSocket client for live market data streaming.
    Wraps SmartWebSocketV2 with async event loop integration.
    """
    
    def __init__(self, auth_manager: AngelAuthManager):
        self.auth = auth_manager
        self.sws: Optional[SmartWebSocketV2] = None
        self.is_connected = False
        self.callbacks: List[Callable] = []
        self.subscribed_tokens: Dict[str, List[str]] = {} # mode -> list of tokens
        
    def _on_data(self, ws, message):
        """Internal callback for raw data"""
        # logger.debug(f"Tick received: {message}")
        # Broadcast to registered callbacks
        for callback in self.callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}")
                
    def _on_open(self, ws):
        logger.info("✅ WebSocket Connection Opened")
        self.is_connected = True
        
    def _on_close(self, ws, *args):
        logger.warning("WebSocket Connection Closed")
        self.is_connected = False
        
    def _on_error(self, ws, error=None, *args):
        logger.error(f"WebSocket Error: {error}")
        
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
            max_retry_attempt=3
        )
        
        # Monkey-patch SDK bug: _on_close and _on_error in SmartWebSocketV2
        orig_on_close = self.sws._on_close
        def patched_on_close(ws, *args):
            try:
                if len(args) == 2:
                    return orig_on_close(ws, args[0], args[1])
                return orig_on_close(ws, *args[:2] if len(args) > 2 else args)
            except Exception:
                pass
        
        self.sws._on_close = patched_on_close

        # Assign callbacks
        self.sws.on_open = self._on_open
        self.sws.on_data = self._on_data
        self.sws.on_error = self._on_error
        self.sws.on_close = self._on_close

    def connect(self):
        """
        Initialize and connect WebSocket (Blocking).
        """
        self._init_sws()
        self.sws.connect()

    def connect_in_thread(self):
        """
        Connect WebSocket in a separate thread (Non-blocking).
        """
        self._init_sws() # Ensure self.sws is set before thread starts
        import threading
        thread = threading.Thread(target=self.connect, daemon=True)
        thread.start()
        return thread
        
    def subscribe(self, mode: int, token_list: List[Dict]):
        """
        Subscribe to a list of tokens.
        """
        if not self.sws:
            logger.warning("WebSocket not initialized. Attempting to connect...")
            self.connect()
        
        # Wait up to 5 seconds for connection if it's already connecting
        import time
        wait_start = time.time()
        while not self.is_connected and time.time() - wait_start < 5:
            time.sleep(0.5)

        if not self.is_connected:
            logger.error("WebSocket not connected after waiting. Subscription may fail.")
            
        try:
            # SmartWebSocketV2 format for correlationID and mode
            correlation_id = "abcde12345" 
            self.sws.subscribe(correlation_id, mode, token_list)
            logger.info(f"Subscribed to {len(token_list)} tokens in mode {mode}")
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            
    def register_callback(self, callback: Callable):
        """Register a function to be called on new ticks"""
        self.callbacks.append(callback)
        
    def close(self):
        if self.sws:
            self.sws.close_connection()

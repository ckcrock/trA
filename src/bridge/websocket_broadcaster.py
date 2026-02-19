import logging
import json
from typing import Any

logger = logging.getLogger(__name__)

class WebSocketBroadcaster:
    """
    Broadcasts ticks to UI clients via WebSocket Hub.
    """
    
    def __init__(self, websocket_manager):
        self.manager = websocket_manager
        
    async def broadcast_tick(self, tick: dict):
        """
        Broadcast tick to 'market_data' channel.
        """
        try:
            message = {
                "type": "TICK",
                "data": tick
            }
            # Assuming manager has a broadcast method
            await self.manager.broadcast("market_data", message)
            
        except Exception as e:
            logger.error(f"Error broadcasting tick to UI: {e}")

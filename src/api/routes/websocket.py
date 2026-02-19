from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Set, Dict, List
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected: {websocket.client}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        # Remove from all subscriptions
        for subscribers in self.subscriptions.values():
            subscribers.discard(websocket)
        logger.info(f"Client disconnected: {websocket.client}")
    
    def subscribe(self, websocket: WebSocket, channel: str):
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(websocket)
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast to all subscribers of a channel"""
        if channel not in self.subscriptions:
            return
        
        disconnected = set()
        message_json = json.dumps(message)
        
        for websocket in self.subscriptions[channel]:
            try:
                await websocket.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(websocket)
        
        # Cleanup disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

# Global Manager Instance
manager = WebSocketManager()

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                
                if action == "subscribe":
                    channel = data.get("channel")
                    if channel:
                        manager.subscribe(websocket, channel)
                        await websocket.send_json({"status": "subscribed", "channel": channel})
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

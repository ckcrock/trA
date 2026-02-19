import pytest
import sys
import os
from unittest.mock import AsyncMock

# Add project root to sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.bridge.websocket_broadcaster import WebSocketBroadcaster

@pytest.mark.asyncio
async def test_broadcast_tick():
    """Verify that broadcast_tick calls manager.broadcast with correct params."""
    # Setup mock manager
    mock_manager = AsyncMock()
    broadcaster = WebSocketBroadcaster(mock_manager)
    
    sample_tick = {
        "symbol": "SBIN-EQ",
        "last_price": 600.5,
        "volume": 1000,
        "timestamp": "2024-01-01T10:00:00"
    }
    
    await broadcaster.broadcast_tick(sample_tick)
    
    # Verify manager.broadcast was called correctly
    mock_manager.broadcast.assert_called_once()
    args, kwargs = mock_manager.broadcast.call_args
    
    assert args[0] == "market_data"
    assert args[1]["type"] == "TICK"
    assert args[1]["data"] == sample_tick

@pytest.mark.asyncio
async def test_broadcast_error_handling():
    """Verify that broadcaster handles errors in manager gracefully."""
    mock_manager = AsyncMock()
    mock_manager.broadcast.side_effect = Exception("Websocket error")
    
    broadcaster = WebSocketBroadcaster(mock_manager)
    
    # Should not raise exception
    await broadcaster.broadcast_tick({"symbol": "TEST"})
    
    mock_manager.broadcast.assert_called_once()

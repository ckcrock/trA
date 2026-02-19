import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import schemas
from src.api.schemas.orders import (
    PlaceOrderRequest, TransactionType, OrderType, ProductType, Duration
)

# -----------------------------------------------------------------------------
# Test Fixture for Mocks
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_deps():
    """Create mocks for all external dependencies."""
    
    # Mock Execution Client
    mock_exec = AsyncMock()
    mock_exec.place_order.return_value = "20240101000001"
    mock_exec.get_order_book.return_value = [{"orderid": "20240101000001", "status": "complete"}]
    mock_exec.get_trade_book.return_value = [{"tradeid": "5001", "orderid": "20240101000001"}]
    mock_exec.get_order_status.return_value = {"orderid": "20240101000001", "status": "complete"}
    mock_exec.cancel_order.return_value = True

    # Mock Lifecycle Manager
    mock_lifecycle = MagicMock()
    mock_lifecycle.get_status.return_value = {"strategy_1": "running"}
    mock_lifecycle.start.return_value = True
    mock_lifecycle.stop.return_value = True
    mock_lifecycle.pause.return_value = True
    mock_lifecycle.resume.return_value = True

    # Mock Health Checker
    mock_health = MagicMock()
    mock_health.get_health.return_value = {"status": "healthy", "components": {}}

    # Mock Auth Manager & Data Bridge
    mock_auth = MagicMock()
    mock_bridge = AsyncMock()
    mock_bridge.start.return_value = None
    mock_bridge.stop.return_value = None
    
    # Mock Trading Node
    mock_node = AsyncMock()
    mock_node.start.return_value = None
    mock_node.stop.return_value = None
    mock_node.lifecycle = mock_lifecycle

    # Mock Websocket Client
    mock_ws = MagicMock()

    return {
        "exec": mock_exec,
        "lifecycle": mock_lifecycle,
        "health": mock_health,
        "auth": mock_auth,
        "bridge": mock_bridge,
        "node": mock_node,
        "ws": mock_ws
    }

@pytest.fixture
def client(mock_deps):
    """Setup TestClient with dependency overrides and global patches."""
    
    # We patch inside the 'src.api.main' namespace because it imports these at the top level
    patches = [
        patch("src.api.main.get_execution_client", return_value=mock_deps["exec"]),
        patch("src.api.main.get_lifecycle_manager", return_value=mock_deps["lifecycle"]),
        patch("src.api.main.get_health_checker", return_value=mock_deps["health"]),
        patch("src.api.main.get_auth_manager", return_value=mock_deps["auth"]),
        patch("src.api.main.get_data_bridge", return_value=mock_deps["bridge"]),
        patch("src.api.main.get_trading_node", return_value=mock_deps["node"]),
        patch("src.api.main.get_ws_client", return_value=mock_deps["ws"]),
        patch("src.api.main.get_symbol_resolver", return_value=MagicMock()),
    ]
    
    for p in patches:
        p.start()

    # Import app AFTER patching
    from src.api.main import app

    # Also set overrides for route-level Depends() which use src.api.dependencies
    from src.api import dependencies
    app.dependency_overrides[dependencies.get_execution_client] = lambda: mock_deps["exec"]
    app.dependency_overrides[dependencies.get_lifecycle_manager] = lambda: mock_deps["lifecycle"]
    app.dependency_overrides[dependencies.get_health_checker] = lambda: mock_deps["health"]

    # Use TestClient as context manager to trigger startup/shutdown events
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    for p in patches:
        p.stop()
    app.dependency_overrides = {}

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_health_check(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "components": {}}

def test_place_order(client, mock_deps):
    """Test POST /api/orders/"""
    payload = {
        "tradingsymbol": "SBIN-EQ",
        "symboltoken": "3045",
        "transactiontype": "BUY",
        "exchange": "NSE",
        "ordertype": "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": 500.5,
        "quantity": 10,
        "variety": "NORMAL"
    }
    
    response = client.post("/api/orders/", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "20240101000001"
    assert data["status"] == "placed"
    
    # Verify mock call
    mock_deps["exec"].place_order.assert_called_once()
    args, kwargs = mock_deps["exec"].place_order.call_args
    assert kwargs["trading_symbol"] == "SBIN-EQ"
    assert kwargs["price"] == 500.5

def test_get_order_book(client):
    """Test GET /api/orders/book"""
    response = client.get("/api/orders/book")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["orderid"] == "20240101000001"

def test_get_order_status(client):
    """Test GET /api/orders/{order_id}"""
    response = client.get("/api/orders/20240101000001")
    assert response.status_code == 200
    assert response.json()["status"] == "complete"

def test_cancel_order(client, mock_deps):
    """Test DELETE /api/orders/{order_id}"""
    response = client.delete("/api/orders/20240101000001")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    
    mock_deps["exec"].cancel_order.assert_called_once_with("20240101000001", "NORMAL")

def test_list_strategies(client):
    """Test GET /api/strategies/"""
    response = client.get("/api/strategies/")
    assert response.status_code == 200
    assert response.json() == {"strategy_1": "running"}

def test_start_strategy(client, mock_deps):
    """Test POST /api/strategies/{name}/start"""
    response = client.post("/api/strategies/my_strat/start")
    assert response.status_code == 200
    assert response.json()["status"] == "started"
    mock_deps["lifecycle"].start.assert_called_with("my_strat")

def test_stop_strategy(client, mock_deps):
    """Test POST /api/strategies/{name}/stop"""
    response = client.post("/api/strategies/my_strat/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"
    mock_deps["lifecycle"].stop.assert_called_with("my_strat")

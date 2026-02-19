# HYBRID ALGORITHMIC TRADING ECOSYSTEM
## System Architecture & Design Specification
### Version 1.0 | Institutional-Grade Production System

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Component Design](#3-component-design)
4. [Directory Structure](#4-directory-structure)
5. [Implementation Phases](#5-implementation-phases)
6. [Workflows & Data Flow](#6-workflows--data-flow)
7. [Requirements Analysis](#7-requirements-analysis)
8. [System Limitations](#8-system-limitations)
9. [Deployment Strategy](#9-deployment-strategy)
10. [Scalability Roadmap](#10-scalability-roadmap)

---

## 1. EXECUTIVE SUMMARY

### 1.1 Vision

Build a **Hybrid Algorithmic Trading Ecosystem** that combines institutional-grade execution infrastructure with a professional trading terminal, enabling both automated algorithmic strategies and manual discretionary trading.

### 1.2 Core Principles

- **Clean Architecture**: Separation of concerns, dependency inversion
- **Event-Driven Design**: Asynchronous, non-blocking operations
- **Production-First**: Built for 24/7 deployment from day one
- **Performance**: Sub-millisecond latency targets
- **Modularity**: Hot-swappable components
- **Observability**: Comprehensive metrics and monitoring

### 1.3 Target Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Order Latency (p95) | < 50ms | Placement to acknowledgment |
| UI Render Rate | < 1ms | Price update to screen |
| Data Throughput | 10k ticks/sec | Sustained load |
| Strategy Hot-Swap | < 5s | Zero downtime |
| System Uptime | 99.9% | Monthly availability |
| Memory Footprint | < 2GB | Base system |

### 1.4 Technology Stack

**Core Trading Engine**
- Nautilus Trader (Cython-optimized event-driven framework)
- Python 3.10+
- asyncio for concurrency

**Backend Orchestration**
- FastAPI (async web framework)
- PostgreSQL (trade persistence)
- Redis (caching & message queue)
- Prometheus (metrics)

**Frontend Terminal**
- Vanilla JavaScript (zero dependencies)
- Lightweight Charts by TradingView
- WebSocket native API
- WebGL for high-performance rendering

**Infrastructure**
- Docker & Docker Compose
- Grafana (visualization)
- nginx (reverse proxy)
- systemd (process management)

---

## 2. SYSTEM ARCHITECTURE

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Web Terminal    │  │  Mobile App      │  │  External Tools  │      │
│  │  (Vanilla JS)    │  │  (Future)        │  │  (TradingView)   │      │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘      │
└───────────┼────────────────────┼────────────────────┼──────────────────┘
            │                    │                    │
            │ WebSocket          │ REST API          │ Webhooks
            │                    │                    │
┌───────────▼────────────────────▼────────────────────▼──────────────────┐
│                      API GATEWAY LAYER                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Backend                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │  │
│  │  │ REST Routes │  │ WebSocket   │  │ Background Task Manager  │ │  │
│  │  │ /orders     │  │ Hub         │  │ - Order reconciliation   │ │  │
│  │  │ /positions  │  │ - Price feed│  │ - Position sync          │ │  │
│  │  │ /strategies │  │ - Orders    │  │ - Health checks          │ │  │
│  │  │ /metrics    │  │ - Events    │  │ - Auto-reconnect         │ │  │
│  │  └─────────────┘  └─────────────┘  └──────────────────────────┘ │  │
│  └────────────────────────┬─────────────────────────────────────────┘  │
└───────────────────────────┼────────────────────────────────────────────┘
                            │
                            │ Internal Message Bus
                            │
┌───────────────────────────▼────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Service Manager                                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │  │
│  │  │ Strategy     │  │ Portfolio    │  │ Risk Manager         │   │  │
│  │  │ Lifecycle    │  │ Supervisor   │  │ - Position limits    │   │  │
│  │  │ Manager      │  │              │  │ - Drawdown control   │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    The Bridge (Data Bus)                          │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │ Event Normalizer & Router                                  │  │  │
│  │  │ - Tick ingestion from WebSocket threads                   │  │  │
│  │  │ - Event transformation                                     │  │  │
│  │  │ - Backpressure handling                                    │  │  │
│  │  │ - Broadcast fanout to Nautilus + UI clients               │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬────────────────────────────────────────────┘
                            │
                            │ Normalized Events
                            │
┌───────────────────────────▼────────────────────────────────────────────┐
│                      EXECUTION LAYER                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Nautilus Trader Core Engine                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │
│  │  │ TradingNode │  │ DataEngine  │  │ ExecutionEngine         │  │  │
│  │  │ - Strategy  │  │ - Cache     │  │ - Order state machine   │  │  │
│  │  │   execution │  │ - Catalog   │  │ - Fill processing       │  │  │
│  │  │ - Event bus │  │ - Ticks/Bars│  │ - Risk checks           │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │  │
│  └────────────────────────┬───────────────────────────────────────────┘  │
│                           │                                              │
│  ┌────────────────────────▼───────────────────────────────────────────┐ │
│  │              Manual Execution Engine                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │ │
│  │  │ Paper       │  │ GTT Order   │  │ Bracket Order Manager   │   │ │
│  │  │ Portfolio   │  │ Manager     │  │ (Entry + SL + Target)   │   │ │
│  │  │ Engine      │  │             │  │                         │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────┬────────────────────────────────────────────┘
                            │
                            │ Order Messages
                            │
┌───────────────────────────▼────────────────────────────────────────────┐
│                      ADAPTER LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              Angel One / SmartAPI Adapters                        │  │
│  │  ┌─────────────────────┐  ┌─────────────────────────────────┐   │  │
│  │  │ DataClient          │  │ ExecutionClient                 │   │  │
│  │  │ - Historical fetch  │  │ - Order placement               │   │  │
│  │  │ - Live WebSocket    │  │ - Modify/cancel                 │   │  │
│  │  │ - Tick normalization│  │ - Status sync                   │   │  │
│  │  │                     │  │ - Rate limiter (10/sec)         │   │  │
│  │  └─────────────────────┘  └─────────────────────────────────┘   │  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐│  │
│  │  │ InstrumentCatalog (SymbolResolver)                           ││  │
│  │  │ - 200k+ instrument CSV parsing                               ││  │
│  │  │ - Multi-index lookup (symbol/token/expiry)                   ││  │
│  │  │ - <1ms resolution time                                       ││  │
│  │  └──────────────────────────────────────────────────────────────┘│  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────┬────────────────────────────────────────────┘
                            │
                            │ Broker API
                            │
┌───────────────────────────▼────────────────────────────────────────────┐
│                      EXTERNAL SYSTEMS                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │ Angel One        │  │ NSE/BSE          │  │ Market Data      │    │
│  │ SmartAPI         │  │ Exchanges        │  │ Providers        │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                      OBSERVABILITY LAYER (Cross-Cutting)                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │ Prometheus       │  │ Grafana          │  │ Structured       │    │
│  │ (Metrics)        │  │ (Dashboards)     │  │ Logging          │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 The Symbiosis Model

The architecture implements a **dual-mode operation**:

**Mode 1: Automated Trading (Headless)**
- TradingNode runs as daemon
- Strategies execute autonomously
- No UI required
- 24/7 operation

**Mode 2: Manual Trading (Terminal)**
- UI-driven execution
- Paper portfolio engine
- Manual order management
- Real-time monitoring

**Shared Infrastructure:**
- Common data feeds
- Unified instrument catalog
- Shared risk management
- Common observability stack

**Critical Design Principle:** Manual and automated operations **MUST NOT** interfere with each other. Separate account management or clear position segregation required.

---

## 3. COMPONENT DESIGN

### 3.1 Trading Engine (Nautilus Trader)

**Architecture Pattern:** Event-Driven, Actor Model

**Core Components:**

```python
# TradingNode - Main orchestrator
class TradingNode:
    """
    Headless trading engine orchestrator.
    Manages strategy lifecycle, data clients, execution clients.
    """
    def __init__(self, config: TradingNodeConfig):
        self.data_engine = DataEngine()
        self.exec_engine = ExecutionEngine()
        self.risk_engine = RiskEngine()
        self.strategies = []
        self.cache = Cache()
        
    async def start(self):
        """Non-blocking start"""
        await self.data_engine.start()
        await self.exec_engine.start()
        for strategy in self.strategies:
            await strategy.start()
    
    async def stop(self):
        """Graceful shutdown"""
        for strategy in self.strategies:
            await strategy.stop()
        await self.exec_engine.stop()
        await self.data_engine.stop()
```

**Strategy Hot-Swapping:**

```python
class StrategyManager:
    """
    Manages strategy lifecycle without downtime.
    """
    async def hot_swap(self, old_strategy: Strategy, new_strategy: Strategy):
        # 1. Pause old strategy (stop new orders)
        await old_strategy.pause()
        
        # 2. Transfer state
        new_strategy.positions = old_strategy.positions
        new_strategy.state = old_strategy.state
        
        # 3. Start new strategy
        await new_strategy.start()
        
        # 4. Stop old strategy
        await old_strategy.stop()
        
        # 5. Update registry
        self.strategies[old_strategy.id] = new_strategy
```

**Performance Characteristics:**
- Event processing: < 100μs
- Order placement: < 10ms (network excluded)
- Strategy execution: < 1ms per tick
- Memory: 100-500MB per strategy

### 3.2 Backend Orchestration (FastAPI)

**Design Pattern:** Dependency Injection, Repository Pattern

**Directory Structure:**

```
/src/api/
├── main.py                 # Application factory
├── dependencies.py         # DI container
├── middleware/
│   ├── auth.py            # JWT authentication
│   ├── logging.py         # Request logging
│   └── metrics.py         # Prometheus instrumentation
├── routes/
│   ├── orders.py          # Order management
│   ├── positions.py       # Position tracking
│   ├── strategies.py      # Strategy control
│   ├── websocket.py       # WebSocket hub
│   └── metrics.py         # Metrics endpoint
├── services/
│   ├── strategy_service.py
│   ├── portfolio_service.py
│   └── order_service.py
└── schemas/
    ├── orders.py          # Pydantic models
    ├── positions.py
    └── strategies.py
```

**Application Initialization:**

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
import asyncio

def create_app() -> FastAPI:
    app = FastAPI(
        title="Trading Platform API",
        version="1.0.0",
        docs_url="/api/docs"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
    
    # Include routers
    app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
    app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
    app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
    app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
    
    # Startup/shutdown events
    @app.on_event("startup")
    async def startup():
        # Initialize background tasks
        app.state.background_tasks = BackgroundTaskManager()
        await app.state.background_tasks.start()
        
        # Initialize Bridge
        app.state.bridge = DataBridge()
        await app.state.bridge.start()
    
    @app.on_event("shutdown")
    async def shutdown():
        await app.state.bridge.stop()
        await app.state.background_tasks.stop()
    
    return app

app = create_app()
```

**WebSocket Hub:**

```python
# routes/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        # Remove from all subscriptions
        for subscribers in self.subscriptions.values():
            subscribers.discard(websocket)
    
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
        
        # Cleanup disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

manager = WebSocketManager()

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "subscribe":
                channel = data.get("channel")
                manager.subscribe(websocket, channel)
                await websocket.send_json({"status": "subscribed", "channel": channel})
            
            elif action == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

**Background Task Manager:**

```python
# services/background_tasks.py
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BackgroundTaskManager:
    def __init__(self):
        self.tasks = []
        self.running = False
    
    async def start(self):
        self.running = True
        self.tasks = [
            asyncio.create_task(self.order_reconciliation()),
            asyncio.create_task(self.position_sync()),
            asyncio.create_task(self.health_check()),
            asyncio.create_task(self.session_refresh()),
        ]
        logger.info("Background tasks started")
    
    async def stop(self):
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        logger.info("Background tasks stopped")
    
    async def order_reconciliation(self):
        """Sync order status every 30 seconds"""
        while self.running:
            try:
                # Fetch all pending orders from broker
                # Compare with local state
                # Update discrepancies
                logger.debug("Order reconciliation cycle")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Order reconciliation error: {e}")
    
    async def position_sync(self):
        """Sync positions every 60 seconds"""
        while self.running:
            try:
                # Fetch positions from broker
                # Update cache
                # Broadcast via WebSocket
                logger.debug("Position sync cycle")
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Position sync error: {e}")
    
    async def health_check(self):
        """System health monitoring every 10 seconds"""
        while self.running:
            try:
                # Check Nautilus engine status
                # Check broker connection
                # Check WebSocket connections
                # Update metrics
                logger.debug("Health check cycle")
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def session_refresh(self):
        """Refresh broker session 30 min before expiry"""
        while self.running:
            try:
                # Check session expiry time
                # Refresh if needed
                logger.debug("Session refresh cycle")
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Session refresh error: {e}")
```

### 3.3 The Bridge (Data Bus)

**Purpose:** Normalize events from multi-threaded WebSocket adapters and distribute to both Nautilus event bus and UI WebSocket clients.

**Architecture:**

```python
# bridge/data_bridge.py
import asyncio
from queue import Queue
from threading import Thread
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class DataBridge:
    """
    Bridge between threaded WebSocket adapters and async event loop.
    Handles backpressure and broadcast fanout.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.subscribers = []  # List of async callbacks
        self.running = False
        self.stats = {
            'ticks_received': 0,
            'ticks_dropped': 0,
            'broadcast_count': 0,
        }
    
    def submit_tick(self, tick: dict):
        """
        Thread-safe tick submission from WebSocket thread.
        Non-blocking - drops tick if queue is full.
        """
        try:
            self.queue.put_nowait(tick)
            self.stats['ticks_received'] += 1
        except asyncio.QueueFull:
            self.stats['ticks_dropped'] += 1
            logger.warning(f"Queue full, dropping tick: {tick['symbol']}")
    
    def subscribe(self, callback: Callable):
        """Register an async callback for tick events"""
        self.subscribers.append(callback)
    
    async def start(self):
        """Start the event processing loop"""
        self.running = True
        asyncio.create_task(self._process_events())
        logger.info("DataBridge started")
    
    async def stop(self):
        """Stop the event processing loop"""
        self.running = False
        logger.info("DataBridge stopped")
    
    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Get tick from queue (with timeout)
                tick = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                
                # Normalize tick data
                normalized_tick = self._normalize_tick(tick)
                
                # Broadcast to all subscribers
                await self._broadcast(normalized_tick)
                
                self.stats['broadcast_count'] += 1
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing tick: {e}")
    
    def _normalize_tick(self, raw_tick: dict) -> dict:
        """Normalize tick to standard format"""
        return {
            'symbol': raw_tick.get('symbol'),
            'timestamp': raw_tick.get('exchange_timestamp'),
            'ltp': float(raw_tick.get('ltp', 0)),
            'bid': float(raw_tick.get('best_bid_price', 0)),
            'ask': float(raw_tick.get('best_ask_price', 0)),
            'volume': int(raw_tick.get('volume', 0)),
            'bid_qty': int(raw_tick.get('best_bid_qty', 0)),
            'ask_qty': int(raw_tick.get('best_ask_qty', 0)),
        }
    
    async def _broadcast(self, tick: dict):
        """Broadcast tick to all subscribers"""
        tasks = [subscriber(tick) for subscriber in self.subscribers]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_stats(self) -> dict:
        """Get bridge statistics"""
        return self.stats.copy()
```

**Integration with Nautilus:**

```python
# bridge/nautilus_integration.py
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.core.datetime import millis_to_nanos

class NautilusBridgeAdapter:
    """Converts normalized ticks to Nautilus QuoteTick objects"""
    
    def __init__(self, data_engine, instrument_provider):
        self.data_engine = data_engine
        self.instrument_provider = instrument_provider
    
    async def on_tick(self, tick: dict):
        """Receive normalized tick and push to Nautilus"""
        try:
            # Resolve instrument
            instrument_id = self.instrument_provider.resolve(tick['symbol'])
            
            # Create QuoteTick
            quote_tick = QuoteTick(
                instrument_id=instrument_id,
                bid_price=tick['bid'],
                ask_price=tick['ask'],
                bid_size=tick['bid_qty'],
                ask_size=tick['ask_qty'],
                ts_event=millis_to_nanos(tick['timestamp']),
                ts_init=millis_to_nanos(tick['timestamp']),
            )
            
            # Push to data engine
            self.data_engine.process(quote_tick)
            
        except Exception as e:
            logger.error(f"Error processing tick for Nautilus: {e}")
```

### 3.4 Broker Adapters (Angel One)

**Rate Limiter Implementation:**

```python
# adapters/angel/rate_limiter.py
import asyncio
import time
from collections import deque
from threading import Lock

class TokenBucketRateLimiter:
    """
    Thread-safe token bucket rate limiter.
    Supports both sync and async usage.
    """
    
    def __init__(self, rate: float, capacity: int = None):
        """
        Args:
            rate: Tokens per second (e.g., 3.0 for 3 req/sec)
            capacity: Bucket capacity (defaults to rate if not specified)
        """
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.tokens = self.capacity
        self.last_update = time.time()
        self.lock = Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens (non-blocking).
        Returns True if acquired, False otherwise.
        """
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    async def acquire_async(self, tokens: int = 1):
        """
        Async version - waits until tokens available.
        """
        while True:
            if self.acquire(tokens):
                return
            # Wait for minimum time to get 1 token
            await asyncio.sleep(1.0 / self.rate)
    
    def wait_and_acquire(self, tokens: int = 1):
        """
        Blocking version - waits until tokens available.
        """
        while not self.acquire(tokens):
            time.sleep(1.0 / self.rate)


class RateLimitedAPIClient:
    """Angel One API client with rate limiting"""
    
    def __init__(self, api_key: str, client_code: str):
        self.client = SmartConnect(api_key)
        # Different rate limits for different endpoint groups
        self.historical_limiter = TokenBucketRateLimiter(rate=3.0)  # 3 req/sec
        self.order_limiter = TokenBucketRateLimiter(rate=10.0)      # 10 req/sec
        self.quote_limiter = TokenBucketRateLimiter(rate=5.0)       # 5 req/sec
    
    async def get_historical_data(self, symbol: str, **kwargs):
        """Rate-limited historical data fetch"""
        await self.historical_limiter.acquire_async()
        return await self._api_call(self.client.getCandleData, symbol, **kwargs)
    
    async def place_order(self, **order_params):
        """Rate-limited order placement"""
        await self.order_limiter.acquire_async()
        return await self._api_call(self.client.placeOrder, **order_params)
    
    async def get_quote(self, symbol: str):
        """Rate-limited quote fetch"""
        await self.quote_limiter.acquire_async()
        return await self._api_call(self.client.getQuote, symbol)
    
    async def _api_call(self, func, *args, **kwargs):
        """Wrapper to handle API calls in async context"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
```

**DataClient Implementation:**

```python
# adapters/angel/data_client.py
from nautilus_trader.adapters.live import LiveDataClient
from nautilus_trader.model.data import QuoteTick, Bar
import asyncio

class AngelDataClient(LiveDataClient):
    """
    Nautilus LiveDataClient implementation for Angel One.
    """
    
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client: SmartConnect,
        msgbus: MessageBus,
        cache: Cache,
        rate_limiter: RateLimitedAPIClient,
    ):
        super().__init__(
            loop=loop,
            client_id=ClientId("ANGEL_ONE"),
            msgbus=msgbus,
            cache=cache,
        )
        self.client = client
        self.rate_limiter = rate_limiter
        self.ws_client = None  # WebSocket client
        self.subscribed_symbols = set()
    
    async def _connect(self):
        """Connect to Angel One WebSocket"""
        # Initialize WebSocket connection
        self.ws_client = AngelWebSocketClient(
            access_token=self.client.access_token,
            feed_token=self.client.feed_token,
            on_tick=self._on_websocket_tick,
        )
        await self.ws_client.connect()
        self._log.info("Connected to Angel One WebSocket")
    
    async def _disconnect(self):
        """Disconnect from WebSocket"""
        if self.ws_client:
            await self.ws_client.disconnect()
        self._log.info("Disconnected from Angel One WebSocket")
    
    async def _subscribe(self, data_type: DataType):
        """Subscribe to data stream"""
        if isinstance(data_type, QuoteTick):
            symbol = data_type.instrument_id.symbol
            await self.ws_client.subscribe(symbol, mode="QUOTE")
            self.subscribed_symbols.add(symbol)
            self._log.info(f"Subscribed to {symbol}")
    
    async def _unsubscribe(self, data_type: DataType):
        """Unsubscribe from data stream"""
        if isinstance(data_type, QuoteTick):
            symbol = data_type.instrument_id.symbol
            await self.ws_client.unsubscribe(symbol)
            self.subscribed_symbols.discard(symbol)
            self._log.info(f"Unsubscribed from {symbol}")
    
    def _on_websocket_tick(self, tick_data: dict):
        """
        Callback from WebSocket thread.
        Submits to Bridge for async processing.
        """
        # Submit to Bridge (thread-safe)
        self._bridge.submit_tick(tick_data)
    
    async def request_historical_bars(
        self,
        instrument_id: InstrumentId,
        bar_type: BarType,
        start: datetime,
        end: datetime,
    ) -> list[Bar]:
        """Fetch historical bars with rate limiting"""
        await self.rate_limiter.historical_limiter.acquire_async()
        
        # Convert to Angel One format
        data = await self.rate_limiter.get_historical_data(
            symbol=str(instrument_id),
            from_date=start,
            to_date=end,
            interval=self._convert_bar_spec(bar_type),
        )
        
        # Convert to Nautilus Bar objects
        bars = self._parse_historical_data(data, instrument_id, bar_type)
        return bars
```

### 3.5 Instrument Catalog (SymbolResolver)

**Performance Requirements:**
- Handle 200,000+ instruments
- < 1ms lookup time
- Multiple index types (symbol, token, expiry)
- In-memory caching

**Implementation:**

```python
# catalog/symbol_resolver.py
import pandas as pd
from typing import Optional, Dict
import logging
from pathlib import Path
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.instruments import Equity, FuturesContract, OptionsContract

logger = logging.getLogger(__name__)

class SymbolResolver:
    """
    High-performance instrument catalog with multiple indexing.
    Parses Angel One scrip master CSV and maintains in-memory indices.
    """
    
    def __init__(self, scrip_master_path: Path):
        self.scrip_master_path = scrip_master_path
        self.instruments: Dict[str, Instrument] = {}
        
        # Multiple indices for fast lookup
        self._symbol_index: Dict[str, str] = {}        # symbol -> instrument_id
        self._token_index: Dict[str, str] = {}         # token -> instrument_id
        self._expiry_index: Dict[str, list] = {}       # expiry -> [instrument_ids]
        
        self._load_instruments()
    
    def _load_instruments(self):
        """Load and parse scrip master CSV"""
        start_time = time.time()
        logger.info(f"Loading instruments from {self.scrip_master_path}")
        
        # Read CSV with optimized dtypes
        df = pd.read_csv(
            self.scrip_master_path,
            dtype={
                'token': str,
                'symbol': str,
                'name': str,
                'expiry': str,
                'strike': 'float64',
                'lotsize': 'int32',
                'instrumenttype': str,
                'exch_seg': str,
                'tick_size': 'float64',
            }
        )
        
        logger.info(f"Loaded {len(df)} instruments from CSV")
        
        # Parse each instrument
        for idx, row in df.iterrows():
            instrument = self._parse_instrument(row)
            if instrument:
                instrument_id = str(instrument.id)
                self.instruments[instrument_id] = instrument
                
                # Build indices
                self._symbol_index[row['symbol']] = instrument_id
                self._token_index[row['token']] = instrument_id
                
                if pd.notna(row['expiry']):
                    expiry = row['expiry']
                    if expiry not in self._expiry_index:
                        self._expiry_index[expiry] = []
                    self._expiry_index[expiry].append(instrument_id)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Loaded {len(self.instruments)} instruments in {elapsed:.2f}s "
            f"({len(self.instruments)/elapsed:.0f} instruments/sec)"
        )
    
    def _parse_instrument(self, row: pd.Series) -> Optional[Instrument]:
        """Parse CSV row to Nautilus Instrument object"""
        try:
            instrument_type = row['instrumenttype'].upper()
            exchange = row['exch_seg']
            symbol = Symbol(row['symbol'])
            
            # Common fields
            instrument_id = InstrumentId(symbol=symbol, venue=exchange)
            
            if instrument_type in ['EQ', 'EQUITY']:
                return Equity(
                    instrument_id=instrument_id,
                    native_symbol=symbol,
                    currency='INR',
                    price_precision=2,
                    price_increment=row['tick_size'],
                    lot_size=row['lotsize'],
                )
            
            elif instrument_type in ['FUTIDX', 'FUTSTK']:
                return FuturesContract(
                    instrument_id=instrument_id,
                    native_symbol=symbol,
                    currency='INR',
                    price_precision=2,
                    price_increment=row['tick_size'],
                    lot_size=row['lotsize'],
                    expiry_date=pd.to_datetime(row['expiry']),
                )
            
            elif instrument_type in ['OPTIDX', 'OPTSTK']:
                option_kind = 'C' if 'CE' in row['symbol'] else 'P'
                return OptionsContract(
                    instrument_id=instrument_id,
                    native_symbol=symbol,
                    currency='INR',
                    price_precision=2,
                    price_increment=row['tick_size'],
                    lot_size=row['lotsize'],
                    expiry_date=pd.to_datetime(row['expiry']),
                    strike_price=row['strike'],
                    option_kind=option_kind,
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to parse instrument {row['symbol']}: {e}")
            return None
    
    def resolve_by_symbol(self, symbol: str, exchange: str = None) -> Optional[Instrument]:
        """Lookup instrument by symbol - O(1) complexity"""
        instrument_id = self._symbol_index.get(symbol)
        return self.instruments.get(instrument_id) if instrument_id else None
    
    def resolve_by_token(self, token: str) -> Optional[Instrument]:
        """Lookup instrument by token - O(1) complexity"""
        instrument_id = self._token_index.get(token)
        return self.instruments.get(instrument_id) if instrument_id else None
    
    def get_by_expiry(self, expiry: str) -> list[Instrument]:
        """Get all instruments expiring on a date - O(1) complexity"""
        instrument_ids = self._expiry_index.get(expiry, [])
        return [self.instruments[id] for id in instrument_ids]
    
    def search(self, query: str, limit: int = 10) -> list[Instrument]:
        """Search instruments by partial symbol match"""
        query_upper = query.upper()
        matches = [
            self.instruments[id]
            for symbol, id in self._symbol_index.items()
            if query_upper in symbol.upper()
        ]
        return matches[:limit]
```

### 3.6 Manual Execution Engine

**Purpose:** Enable manual trading without interfering with automated strategies.

**Components:**

1. **Paper Portfolio Engine** - Simulates portfolio for manual trades
2. **GTT Order Manager** - Good Till Trigger orders
3. **Bracket Order Manager** - Entry + SL + Target in single workflow

**Implementation:**

```python
# manual/portfolio_engine.py
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class Position:
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    pnl_percent: float

class OrderStatus(Enum):
    PENDING = "PENDING"
    TRIGGERED = "TRIGGERED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class GTTOrder:
    """Good Till Trigger order"""
    symbol: str
    trigger_price: float
    quantity: int
    order_type: str  # "MARKET" or "LIMIT"
    limit_price: Optional[float]
    status: OrderStatus
    triggered_at: Optional[datetime]

class PaperPortfolioEngine:
    """
    Simulated portfolio for manual trading.
    Does NOT execute real orders - for UI practice only.
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.capital = initial_capital
        self.available_margin = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, GTTOrder] = {}
        self.trade_history = []
    
    def place_market_order(self, symbol: str, quantity: int, price: float):
        """Simulate market order execution"""
        # Calculate cost
        cost = abs(quantity) * price
        
        # Check margin
        if cost > self.available_margin:
            raise ValueError("Insufficient margin")
        
        # Update position
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_quantity = pos.quantity + quantity
            total_cost = (pos.quantity * pos.avg_price) + (quantity * price)
            
            if total_quantity == 0:
                # Position closed
                del self.positions[symbol]
                self.available_margin += cost
            else:
                # Update position
                pos.quantity = total_quantity
                pos.avg_price = total_cost / total_quantity
        else:
            # New position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                current_price=price,
                pnl=0.0,
                pnl_percent=0.0,
            )
            self.available_margin -= cost
        
        # Record trade
        self.trade_history.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
        })
    
    def place_gtt_order(self, symbol: str, trigger_price: float, quantity: int, 
                        order_type: str = "MARKET", limit_price: Optional[float] = None):
        """Place Good Till Trigger order"""
        order_id = f"GTT_{len(self.orders) + 1}"
        self.orders[order_id] = GTTOrder(
            symbol=symbol,
            trigger_price=trigger_price,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            status=OrderStatus.PENDING,
            triggered_at=None,
        )
        return order_id
    
    def update_market_price(self, symbol: str, price: float):
        """Update current market price and check GTT triggers"""
        # Update position PnL
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = price
            pos.pnl = (price - pos.avg_price) * pos.quantity
            pos.pnl_percent = (pos.pnl / (pos.avg_price * abs(pos.quantity))) * 100
        
        # Check GTT triggers
        for order_id, order in self.orders.items():
            if order.symbol == symbol and order.status == OrderStatus.PENDING:
                if (order.quantity > 0 and price >= order.trigger_price) or \
                   (order.quantity < 0 and price <= order.trigger_price):
                    # Trigger order
                    order.status = OrderStatus.TRIGGERED
                    order.triggered_at = datetime.now()
                    # Execute order
                    execution_price = order.limit_price if order.order_type == "LIMIT" else price
                    self.place_market_order(symbol, order.quantity, execution_price)
                    order.status = OrderStatus.FILLED
    
    def get_portfolio_summary(self) -> dict:
        """Get portfolio summary"""
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        return {
            'capital': self.capital,
            'available_margin': self.available_margin,
            'positions_count': len(self.positions),
            'total_pnl': total_pnl,
            'total_pnl_percent': (total_pnl / self.capital) * 100,
        }


class BracketOrderManager:
    """
    Manages bracket orders (Entry + SL + Target).
    Automatically places SL and Target when entry fills.
    """
    
    def __init__(self, portfolio_engine: PaperPortfolioEngine):
        self.portfolio = portfolio_engine
        self.bracket_orders: Dict[str, dict] = {}
    
    def place_bracket_order(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
    ) -> str:
        """Place bracket order with entry, SL, and target"""
        order_id = f"BRACKET_{len(self.bracket_orders) + 1}"
        
        # Create bracket order
        self.bracket_orders[order_id] = {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target': target,
            'status': 'PENDING',
            'entry_filled': False,
            'sl_order_id': None,
            'target_order_id': None,
        }
        
        # Place entry order (GTT)
        entry_order_id = self.portfolio.place_gtt_order(
            symbol=symbol,
            trigger_price=entry_price,
            quantity=quantity,
            order_type="LIMIT",
            limit_price=entry_price,
        )
        
        self.bracket_orders[order_id]['entry_order_id'] = entry_order_id
        
        return order_id
    
    def check_entry_fills(self):
        """Check if entry orders are filled and place SL/Target"""
        for order_id, bracket in self.bracket_orders.items():
            if bracket['status'] == 'PENDING' and not bracket['entry_filled']:
                entry_order = self.portfolio.orders[bracket['entry_order_id']]
                
                if entry_order.status == OrderStatus.FILLED:
                    # Entry filled, place SL and Target
                    bracket['entry_filled'] = True
                    
                    # Place stop loss
                    sl_order_id = self.portfolio.place_gtt_order(
                        symbol=bracket['symbol'],
                        trigger_price=bracket['stop_loss'],
                        quantity=-bracket['quantity'],  # Opposite direction
                        order_type="MARKET",
                    )
                    bracket['sl_order_id'] = sl_order_id
                    
                    # Place target
                    target_order_id = self.portfolio.place_gtt_order(
                        symbol=bracket['symbol'],
                        trigger_price=bracket['target'],
                        quantity=-bracket['quantity'],  # Opposite direction
                        order_type="MARKET",
                    )
                    bracket['target_order_id'] = target_order_id
                    
                    bracket['status'] = 'ACTIVE'
```

### 3.7 Observability Layer

**Prometheus Metrics:**

```python
# observability/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from functools import wraps
import time

# Order metrics
orders_placed_total = Counter(
    'orders_placed_total',
    'Total orders placed',
    ['order_type', 'symbol', 'side']
)

order_placement_duration = Histogram(
    'order_placement_duration_seconds',
    'Time to place order',
    ['order_type'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

order_rejections_total = Counter(
    'order_rejections_total',
    'Total order rejections',
    ['reason']
)

# WebSocket metrics
websocket_connections = Gauge(
    'websocket_connections',
    'Number of active WebSocket connections',
    ['type']
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total WebSocket messages',
    ['direction', 'type']
)

# Strategy metrics
strategy_execution_duration = Histogram(
    'strategy_execution_duration_seconds',
    'Strategy execution time',
    ['strategy_name'],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1]
)

active_strategies = Gauge(
    'active_strategies',
    'Number of active strategies'
)

# API metrics
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint', 'status'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# System metrics
bridge_queue_size = Gauge(
    'bridge_queue_size',
    'Size of Bridge event queue'
)

bridge_ticks_dropped = Counter(
    'bridge_ticks_dropped_total',
    'Total ticks dropped due to backpressure'
)

# Angel API metrics
angel_api_calls_total = Counter(
    'angel_api_calls_total',
    'Total Angel API calls',
    ['endpoint', 'status']
)

angel_api_rate_limit_errors = Counter(
    'angel_api_rate_limit_errors_total',
    'Rate limit errors from Angel API'
)

# Decorators
def track_time(metric_name: str):
    """Decorator to track execution time"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                
                if metric_name == "order_latency":
                    order_placement_duration.labels(
                        order_type=kwargs.get('order_type', 'UNKNOWN')
                    ).observe(duration)
                elif metric_name == "strategy_execution":
                    strategy_execution_duration.labels(
                        strategy_name=kwargs.get('strategy_name', 'UNKNOWN')
                    ).observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start
                raise
        return wrapper
    return decorator
```

**Grafana Dashboard Configuration (JSON):**

```json
{
  "dashboard": {
    "title": "Trading Platform - Main Dashboard",
    "panels": [
      {
        "id": 1,
        "title": "Order Placement Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(order_placement_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "id": 2,
        "title": "Orders Per Minute",
        "targets": [
          {
            "expr": "rate(orders_placed_total[1m]) * 60"
          }
        ],
        "type": "graph"
      },
      {
        "id": 3,
        "title": "Order Rejection Rate",
        "targets": [
          {
            "expr": "rate(order_rejections_total[5m])"
          }
        ],
        "type": "graph"
      },
      {
        "id": 4,
        "title": "WebSocket Connections",
        "targets": [
          {
            "expr": "websocket_connections"
          }
        ],
        "type": "stat"
      },
      {
        "id": 5,
        "title": "Bridge Queue Backpressure",
        "targets": [
          {
            "expr": "bridge_queue_size"
          }
        ],
        "type": "graph"
      },
      {
        "id": 6,
        "title": "API Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

### 3.8 Frontend Terminal

**Architecture:**

```
/src/ui/
├── index.html
├── css/
│   ├── main.css           # Base styles
│   ├── components.css     # Component-specific styles
│   └── theme.css          # Color scheme and design tokens
├── js/
│   ├── main.js            # Application entry point
│   ├── websocket.js       # WebSocket manager
│   ├── components/
│   │   ├── Chart.js       # Price chart component
│   │   ├── OrderPanel.js  # Order placement
│   │   ├── PositionsPanel.js # Positions display
│   │   ├── Heatmap.js     # Slippage/latency heatmap
│   │   └── OrderBook.js   # Order book display
│   ├── utils/
│   │   ├── formatters.js  # Number/date formatters
│   │   └── keyboard.js    # Keyboard shortcuts
│   └── state/
│       └── store.js       # Client-side state management
└── assets/
    └── icons/
```

**WebSocket Manager:**

```javascript
// js/websocket.js
class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.subscribers = new Map();
        this.messageQueue = [];
    }
    
    connect() {
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.flushMessageQueue();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed');
            this.reconnect();
        };
    }
    
    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            console.log(`Reconnecting in ${delay}ms...`);
            setTimeout(() => this.connect(), delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
    
    subscribe(channel, callback) {
        if (!this.subscribers.has(channel)) {
            this.subscribers.set(channel, new Set());
        }
        this.subscribers.get(channel).add(callback);
        
        // Send subscribe message
        this.send({
            action: 'subscribe',
            channel: channel
        });
    }
    
    unsubscribe(channel, callback) {
        if (this.subscribers.has(channel)) {
            this.subscribers.get(channel).delete(callback);
        }
    }
    
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            this.messageQueue.push(message);
        }
    }
    
    flushMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.send(message);
        }
    }
    
    handleMessage(data) {
        const channel = data.channel || 'default';
        if (this.subscribers.has(channel)) {
            this.subscribers.get(channel).forEach(callback => {
                callback(data);
            });
        }
    }
}
```

**Chart Component (Lightweight Charts):**

```javascript
// js/components/Chart.js
import { createChart } from 'lightweight-charts';

class ChartComponent {
    constructor(container) {
        this.container = container;
        this.chart = null;
        this.series = null;
        this.lastUpdate = 0;
        this.updateThrottle = 16; // ~60fps
        this.init();
    }
    
    init() {
        this.chart = createChart(this.container, {
            width: this.container.clientWidth,
            height: this.container.clientHeight,
            layout: {
                background: { color: '#0A0F1C' },
                textColor: '#DDD',
            },
            grid: {
                vertLines: { color: '#1a1f2e' },
                horzLines: { color: '#1a1f2e' },
            },
            crosshair: {
                mode: 1,
            },
            timeScale: {
                borderColor: '#2B2B43',
                timeVisible: true,
                secondsVisible: true,
            },
        });
        
        this.series = this.chart.addCandlestickSeries({
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            this.chart.applyOptions({
                width: this.container.clientWidth,
                height: this.container.clientHeight,
            });
        });
    }
    
    updateTick(tick) {
        // Throttle updates for performance
        const now = Date.now();
        if (now - this.lastUpdate < this.updateThrottle) {
            return;
        }
        this.lastUpdate = now;
        
        // Update last candle or create new one
        const candle = {
            time: tick.timestamp / 1000, // Convert to seconds
            open: tick.open || tick.ltp,
            high: tick.high || tick.ltp,
            low: tick.low || tick.ltp,
            close: tick.ltp,
        };
        
        this.series.update(candle);
    }
    
    setData(bars) {
        this.series.setData(bars);
    }
}
```

**Order Panel:**

```javascript
// js/components/OrderPanel.js
class OrderPanel {
    constructor(container, wsManager) {
        this.container = container;
        this.ws = wsManager;
        this.render();
        this.attachEventListeners();
    }
    
    render() {
        this.container.innerHTML = `
            <div class="order-panel glass-panel">
                <div class="panel-header">
                    <h3>Place Order</h3>
                </div>
                <div class="panel-body">
                    <div class="form-group">
                        <label>Symbol</label>
                        <input type="text" id="symbol-input" placeholder="SBIN, NIFTY, etc.">
                    </div>
                    <div class="form-group">
                        <label>Quantity</label>
                        <input type="number" id="quantity-input" value="1">
                    </div>
                    <div class="form-group">
                        <label>Order Type</label>
                        <select id="order-type-select">
                            <option value="MARKET">Market</option>
                            <option value="LIMIT">Limit</option>
                            <option value="STOPLOSS">Stop Loss</option>
                        </select>
                    </div>
                    <div class="form-group" id="price-group" style="display:none;">
                        <label>Price</label>
                        <input type="number" id="price-input" step="0.05">
                    </div>
                    <div class="button-group">
                        <button class="btn btn-buy" id="buy-btn">BUY</button>
                        <button class="btn btn-sell" id="sell-btn">SELL</button>
                    </div>
                </div>
            </div>
        `;
    }
    
    attachEventListeners() {
        const orderTypeSelect = document.getElementById('order-type-select');
        const priceGroup = document.getElementById('price-group');
        
        orderTypeSelect.addEventListener('change', (e) => {
            if (e.target.value === 'MARKET') {
                priceGroup.style.display = 'none';
            } else {
                priceGroup.style.display = 'block';
            }
        });
        
        document.getElementById('buy-btn').addEventListener('click', () => {
            this.placeOrder('BUY');
        });
        
        document.getElementById('sell-btn').addEventListener('click', () => {
            this.placeOrder('SELL');
        });
    }
    
    placeOrder(side) {
        const symbol = document.getElementById('symbol-input').value;
        const quantity = parseInt(document.getElementById('quantity-input').value);
        const orderType = document.getElementById('order-type-select').value;
        const price = orderType !== 'MARKET' ? 
            parseFloat(document.getElementById('price-input').value) : null;
        
        const order = {
            symbol,
            quantity,
            side,
            order_type: orderType,
            price,
        };
        
        // Send to backend via WebSocket
        this.ws.send({
            action: 'place_order',
            data: order
        });
        
        // Visual feedback
        this.showOrderFeedback(side);
    }
    
    showOrderFeedback(side) {
        const btn = side === 'BUY' ? 
            document.getElementById('buy-btn') : 
            document.getElementById('sell-btn');
        
        btn.classList.add('pulse-animation');
        setTimeout(() => {
            btn.classList.remove('pulse-animation');
        }, 1000);
    }
}
```

**CSS Theme (Ferrari Cockpit):**

```css
/* css/theme.css */
:root {
    --bg-dark: #0A0F1C;
    --bg-panel: rgba(20, 30, 48, 0.8);
    --border-color: rgba(255, 255, 255, 0.1);
    --text-primary: #E0E6ED;
    --text-secondary: #8B93A7;
    --accent-green: #00FF88;
    --accent-red: #FF3860;
    --accent-blue: #00D4FF;
    --glow-green: rgba(0, 255, 136, 0.4);
    --glow-red: rgba(255, 56, 96, 0.4);
}

body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg-dark);
    color: var(--text-primary);
    overflow: hidden;
}

.glass-panel {
    background: var(--bg-panel);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.btn {
    padding: 12px 24px;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.btn-buy {
    background: linear-gradient(135deg, var(--accent-green), #00CC70);
    color: #000;
    box-shadow: 0 4px 20px var(--glow-green);
}

.btn-buy:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 30px var(--glow-green);
}

.btn-sell {
    background: linear-gradient(135deg, var(--accent-red), #CC2844);
    color: #fff;
    box-shadow: 0 4px 20px var(--glow-red);
}

.btn-sell:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 30px var(--glow-red);
}

.pulse-animation {
    animation: pulse 0.5s ease-in-out;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

/* Price update animation */
.price-up {
    color: var(--accent-green);
    animation: glow-green 0.5s ease-out;
}

.price-down {
    color: var(--accent-red);
    animation: glow-red 0.5s ease-out;
}

@keyframes glow-green {
    0% { text-shadow: 0 0 20px var(--glow-green); }
    100% { text-shadow: 0 0 0 transparent; }
}

@keyframes glow-red {
    0% { text-shadow: 0 0 20px var(--glow-red); }
    100% { text-shadow: 0 0 0 transparent; }
}
```

---

## 4. DIRECTORY STRUCTURE

### 4.1 Complete Project Layout

```
trading-platform/
│
├── README.md                          # Project overview and quick start
├── ARCHITECTURE.md                    # Detailed architecture documentation
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata and build config
├── Dockerfile                         # Main application container
├── docker-compose.yml                 # Multi-container orchestration
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
│
├── config/                            # Configuration files
│   ├── trading_node.yaml              # Nautilus TradingNode config
│   ├── backtest.yaml                  # Backtest configuration
│   ├── strategies/                    # Strategy-specific configs
│   │   ├── ema_crossover.yaml
│   │   └── breakout.yaml
│   ├── risk_limits.yaml               # Risk management rules
│   └── logging.yaml                   # Logging configuration
│
├── src/                               # Main source code
│   │
│   ├── __init__.py
│   │
│   ├── engine/                        # Nautilus Trading Engine
│   │   ├── __init__.py
│   │   ├── node.py                    # TradingNode wrapper
│   │   ├── config_loader.py           # Configuration management
│   │   └── lifecycle.py               # Strategy lifecycle management
│   │
│   ├── adapters/                      # Broker adapters
│   │   ├── __init__.py
│   │   ├── angel/                     # Angel One adapter
│   │   │   ├── __init__.py
│   │   │   ├── data_client.py         # Angel DataClient
│   │   │   ├── execution_client.py    # Angel ExecutionClient
│   │   │   ├── websocket_client.py    # WebSocket handler
│   │   │   ├── rate_limiter.py        # Token bucket limiter
│   │   │   └── auth.py                # Authentication manager
│   │   └── common/
│   │       ├── __init__.py
│   │       └── base.py                # Base adapter classes
│   │
│   ├── catalog/                       # Instrument catalog
│   │   ├── __init__.py
│   │   ├── symbol_resolver.py         # Symbol lookup service
│   │   ├── instrument_parser.py       # CSV parser
│   │   └── cache.py                   # In-memory caching
│   │
│   ├── bridge/                        # Data Bridge
│   │   ├── __init__.py
│   │   ├── data_bridge.py             # Main bridge implementation
│   │   ├── nautilus_adapter.py        # Nautilus integration
│   │   └── websocket_broadcaster.py   # UI broadcast
│   │
│   ├── manual/                        # Manual trading engine
│   │   ├── __init__.py
│   │   ├── portfolio_engine.py        # Paper portfolio
│   │   ├── gtt_manager.py             # GTT orders
│   │   ├── bracket_orders.py          # Bracket order logic
│   │   └── risk_validator.py          # Risk checks
│   │
│   ├── strategies/                    # Trading strategies
│   │   ├── __init__.py
│   │   ├── base/
│   │   │   ├── __init__.py
│   │   │   └── strategy_base.py       # Base strategy class
│   │   ├── momentum/
│   │   │   ├── __init__.py
│   │   │   ├── ema_crossover.py       # EMA strategy
│   │   │   └── rsi_breakout.py        # RSI strategy
│   │   └── mean_reversion/
│   │       ├── __init__.py
│   │       └── bollinger_bounce.py    # BB strategy
│   │
│   ├── observability/                 # Metrics and monitoring
│   │   ├── __init__.py
│   │   ├── metrics.py                 # Prometheus metrics
│   │   ├── logging_config.py          # Structured logging
│   │   └── health_check.py            # Health endpoints
│   │
│   ├── api/                           # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py                    # Application factory
│   │   ├── dependencies.py            # Dependency injection
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                # JWT authentication
│   │   │   ├── logging.py             # Request logging
│   │   │   └── cors.py                # CORS configuration
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── orders.py              # Order management
│   │   │   ├── positions.py           # Position tracking
│   │   │   ├── strategies.py          # Strategy control
│   │   │   ├── market_data.py         # Market data endpoints
│   │   │   ├── websocket.py           # WebSocket hub
│   │   │   └── metrics.py             # Metrics endpoint
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── strategy_service.py    # Strategy management
│   │   │   ├── portfolio_service.py   # Portfolio operations
│   │   │   ├── order_service.py       # Order operations
│   │   │   └── background_tasks.py    # Background workers
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── orders.py              # Order models
│   │       ├── positions.py           # Position models
│   │       └── strategies.py          # Strategy models
│   │
│   ├── ui/                            # Frontend terminal
│   │   ├── index.html                 # Main HTML
│   │   ├── css/
│   │   │   ├── main.css               # Base styles
│   │   │   ├── components.css         # Component styles
│   │   │   └── theme.css              # Design system
│   │   ├── js/
│   │   │   ├── main.js                # App entry
│   │   │   ├── websocket.js           # WebSocket manager
│   │   │   ├── components/
│   │   │   │   ├── Chart.js           # Chart component
│   │   │   │   ├── OrderPanel.js      # Order panel
│   │   │   │   ├── PositionsPanel.js  # Positions display
│   │   │   │   ├── Heatmap.js         # Heatmap visualization
│   │   │   │   └── OrderBook.js       # Order book
│   │   │   ├── utils/
│   │   │   │   ├── formatters.js      # Formatters
│   │   │   │   └── keyboard.js        # Shortcuts
│   │   │   └── state/
│   │   │       └── store.js           # State management
│   │   └── assets/
│   │       ├── icons/
│   │       └── fonts/
│   │
│   └── utils/                         # Utility functions
│       ├── __init__.py
│       ├── time_utils.py              # Time conversions
│       ├── validators.py              # Input validation
│       └── constants.py               # System constants
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_adapters.py
│   │   ├── test_bridge.py
│   │   ├── test_catalog.py
│   │   └── test_manual_engine.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_websocket.py
│   │   └── test_end_to_end.py
│   └── fixtures/
│       ├── sample_ticks.json
│       └── sample_orders.json
│
├── data/                              # Data storage
│   ├── catalog/                       # Nautilus catalog (Parquet)
│   ├── instruments/                   # Instrument master files
│   │   └── angel_scrip_master.csv
│   ├── logs/                          # Application logs
│   └── backtest_results/              # Backtest outputs
│
├── scripts/                           # Utility scripts
│   ├── download_instruments.py        # Fetch scrip master
│   ├── backtest_runner.py             # Run backtests
│   ├── deploy.sh                      # Deployment script
│   └── setup_database.py              # Database initialization
│
├── monitoring/                        # Monitoring stack
│   ├── prometheus/
│   │   ├── prometheus.yml             # Prometheus config
│   │   └── rules/
│   │       └── alerts.yml             # Alert rules
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   └── prometheus.yml
│       │   └── dashboards/
│       │       └── dashboard.yml
│       └── dashboards/
│           ├── trading_platform.json  # Main dashboard
│           ├── slippage_analysis.json # Slippage dashboard
│           └── strategy_performance.json
│
└── docs/                              # Documentation
    ├── API.md                         # API documentation
    ├── DEPLOYMENT.md                  # Deployment guide
    ├── STRATEGIES.md                  # Strategy development guide
    ├── OBSERVABILITY.md               # Monitoring guide
    └── TROUBLESHOOTING.md             # Common issues
```

---

## 5. IMPLEMENTATION PHASES

### Phase 1: Foundation (Weeks 1-2)

**Goal:** Establish core infrastructure and basic functionality

**Deliverables:**
- ✅ Project structure setup
- ✅ Angel One adapter (basic data + execution)
- ✅ Instrument catalog with symbol resolver
- ✅ Basic Nautilus integration
- ✅ FastAPI backend skeleton
- ✅ Docker setup

**Tasks:**
1. Initialize project with Poetry/setuptools
2. Implement Angel One authentication
3. Create DataClient for historical data fetch
4. Create ExecutionClient for order placement
5. Implement SymbolResolver with CSV parsing
6. Set up FastAPI with basic routes
7. Create Dockerfile and docker-compose.yml
8. Write unit tests for adapters

**Success Criteria:**
- Can fetch historical data from Angel One
- Can place test orders (paper mode)
- Symbol resolution < 1ms
- All tests passing
- Docker containers running

### Phase 2: Data Bridge & WebSocket (Weeks 3-4)

**Goal:** Implement real-time data flow

**Deliverables:**
- ✅ Angel WebSocket client
- ✅ Data Bridge implementation
- ✅ Nautilus integration
- ✅ UI WebSocket hub
- ✅ Reconnection logic
- ✅ Backpressure handling

**Tasks:**
1. Implement Angel WebSocket V2 client
2. Create DataBridge with asyncio queue
3. Integrate Bridge with Nautilus event bus
4. Create WebSocket endpoint in FastAPI
5. Implement broadcast fanout
6. Add reconnection logic with exponential backoff
7. Implement queue backpressure monitoring
8. Load test with 10k ticks/sec

**Success Criteria:**
- Stable WebSocket connection for 24 hours
- < 10ms latency from tick receive to UI
- Zero data loss under normal load
- Automatic reconnection working
- Prometheus metrics exposed

### Phase 3: Trading Engine & Strategies (Weeks 5-7)

**Goal:** Complete automated trading capabilities

**Deliverables:**
- ✅ TradingNode configuration
- ✅ Strategy hot-swapping
- ✅ Sample strategies (3-5)
- ✅ Backtest framework
- ✅ Risk management
- ✅ Performance analytics

**Tasks:**
1. Configure Nautilus TradingNode
2. Implement strategy lifecycle manager
3. Create sample EMA crossover strategy
4. Create sample RSI breakout strategy
5. Create sample Bollinger Bands strategy
6. Implement hot-swap mechanism
7. Set up backtest configuration
8. Run backtests on 6 months of data
9. Implement risk limits (position size, drawdown)
10. Create performance report generator

**Success Criteria:**
- Can run strategies in live mode
- Hot-swap completes in < 5 seconds
- Backtests match live behavior (within 1%)
- Risk limits enforced correctly
- Strategy execution < 1ms per tick

### Phase 4: Manual Trading & UI (Weeks 8-10)

**Goal:** Build professional trading terminal

**Deliverables:**
- ✅ Frontend terminal (Vanilla JS)
- ✅ Paper portfolio engine
- ✅ GTT order manager
- ✅ Bracket order support
- ✅ Real-time price charts
- ✅ Position tracking

**Tasks:**
1. Design UI layout (Figma mockup)
2. Implement chart component with Lightweight Charts
3. Create order panel with keyboard shortcuts
4. Build positions panel with P&L tracking
5. Implement PaperPortfolioEngine
6. Create GTT order manager
7. Create bracket order workflow
8. Add heatmap visualization (latency/slippage)
9. Implement WebSocket streaming to UI
10. Add price update animations

**Success Criteria:**
- UI renders prices in < 1ms
- Zero UI blocking during updates
- Keyboard shortcuts functional
- Paper portfolio accurate
- GTT and bracket orders working

### Phase 5: Observability & Production Hardening (Weeks 11-12)

**Goal:** Make system production-ready

**Deliverables:**
- ✅ Prometheus metrics
- ✅ Grafana dashboards
- ✅ Structured logging
- ✅ Health checks
- ✅ Alert rules
- ✅ Deployment automation

**Tasks:**
1. Instrument code with Prometheus metrics
2. Create Grafana dashboards (5+)
3. Implement structured JSON logging
4. Add health check endpoints
5. Create Prometheus alert rules
6. Set up log aggregation
7. Create deployment scripts
8. Write runbooks for common issues
9. Perform load testing (10x normal load)
10. Conduct security audit

**Success Criteria:**
- All key metrics exposed
- Dashboards provide actionable insights
- Alerts fire correctly
- Deployment automated
- Passes load test (10k orders/min)
- Zero critical security issues

### Phase 6: Scale Testing & Optimization (Weeks 13-14)

**Goal:** Validate 10x scalability

**Deliverables:**
- ✅ Load test results
- ✅ Performance optimizations
- ✅ Horizontal scaling capability
- ✅ Disaster recovery plan

**Tasks:**
1. Conduct load testing
   - 100k ticks/sec
   - 10k orders/min
   - 100 concurrent strategies
2. Profile for bottlenecks
3. Optimize critical paths
4. Implement connection pooling
5. Add database indices
6. Test horizontal scaling (multiple nodes)
7. Create disaster recovery procedures
8. Test failover scenarios
9. Document capacity limits
10. Create scaling runbook

**Success Criteria:**
- System handles 10x load
- p95 latency < 100ms under 10x load
- Horizontal scaling working
- Failover time < 30 seconds
- Clear capacity documentation

---

## 6. WORKFLOWS & DATA FLOW

### 6.1 Market Data Flow

```
┌─────────────────┐
│ Angel SmartAPI  │
│ WebSocket Feed  │
└────────┬────────┘
         │ (Threaded)
         ▼
┌─────────────────────────┐
│  WebSocket Client       │
│  - Tick normalization   │
│  - Error handling       │
└────────┬────────────────┘
         │ submit_tick()
         ▼
┌─────────────────────────┐
│  Data Bridge            │
│  - asyncio.Queue        │
│  - Backpressure         │
│  - Broadcast fanout     │
└─────┬──────────────┬────┘
      │              │
      ▼              ▼
┌─────────────┐  ┌──────────────┐
│  Nautilus   │  │  WebSocket   │
│  Event Bus  │  │  Manager     │
└─────┬───────┘  └──────┬───────┘
      │                 │
      ▼                 ▼
┌─────────────┐  ┌──────────────┐
│ Strategies  │  │  UI Clients  │
│ - Execution │  │  - Chart     │
│ - Signals   │  │  - OrderBook │
└─────────────┘  └──────────────┘
```

**Latency Budget:**
- WebSocket receive: 5ms
- Bridge processing: 2ms
- Nautilus processing: 3ms
- Strategy execution: 1ms
- UI render: 1ms
**Total: ~12ms**

### 6.2 Order Execution Flow

```
┌─────────────────┐
│  UI / Strategy  │
│  Order Request  │
└────────┬────────┘
         │
         ▼
┌──────────────────────────┐
│  FastAPI Backend         │
│  - Validation            │
│  - Risk checks           │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Execution Client        │
│  - Rate limiting         │
│  - Order formatting      │
└────────┬─────────────────┘
         │ HTTP/REST
         ▼
┌──────────────────────────┐
│  Angel SmartAPI          │
│  - Order placement       │
│  - Validation            │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Exchange (NSE/BSE)      │
│  - Order matching        │
└────────┬─────────────────┘
         │ (Order updates via WebSocket)
         ▼
┌──────────────────────────┐
│  Execution Reports       │
│  - Fill notifications    │
│  - Status updates        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Portfolio Update        │
│  - Position tracking     │
│  - P&L calculation       │
└──────────────────────────┘
```

**Latency Targets:**
- Order validation: < 5ms
- API call: < 30ms (network)
- Total order latency (p95): < 50ms

### 6.3 Strategy Execution Workflow

```
1. Data Ingestion
   ├── Tick received from Bridge
   ├── Tick cached in DataEngine
   └── Strategies notified

2. Strategy Processing
   ├── on_quote_tick() called
   ├── Indicator calculation
   ├── Signal generation
   └── Decision: BUY/SELL/HOLD

3. Order Generation
   ├── Position size calculation
   ├── Risk checks (limits)
   ├── Order construction
   └── Submit to ExecutionEngine

4. Order Routing
   ├── ExecutionEngine receives order
   ├── Pre-trade risk validation
   ├── Route to ExecutionClient
   └── Send to broker

5. Fill Processing
   ├── Fill notification from broker
   ├── Update position in Cache
   ├── Calculate realized P&L
   ├── Notify strategy (on_order_filled)
   └── Broadcast to UI

6. Performance Tracking
   ├── Record trade in database
   ├── Update metrics (Prometheus)
   ├── Calculate performance stats
   └── Update Grafana dashboard
```

### 6.4 Hot-Swap Workflow

```
1. Preparation
   ├── Load new strategy code
   ├── Validate configuration
   └── Initialize new strategy instance

2. State Transfer
   ├── Pause old strategy (stop new orders)
   ├── Export state (positions, indicators)
   ├── Import state to new strategy
   └── Verify state consistency

3. Switch
   ├── Unregister old strategy from event bus
   ├── Register new strategy
   ├── Start new strategy
   └── Update registry

4. Cleanup
   ├── Stop old strategy gracefully
   ├── Archive logs and metrics
   ├── Free resources
   └── Confirm successful swap

Total time: < 5 seconds
```

---

## 7. REQUIREMENTS ANALYSIS

### 7.1 Functional Requirements

**FR-001:** System shall support real-time market data streaming
**FR-002:** System shall execute market, limit, and stop-loss orders
**FR-003:** System shall support automated strategy execution
**FR-004:** System shall support manual order placement
**FR-005:** System shall track positions and calculate P&L in real-time
**FR-006:** System shall support hot-swapping of strategies
**FR-007:** System shall maintain order history and audit trail
**FR-008:** System shall support backtesting with historical data
**FR-009:** System shall enforce risk limits (position size, drawdown)
**FR-010:** System shall provide real-time performance metrics
**FR-011:** System shall support GTT (Good Till Trigger) orders
**FR-012:** System shall support bracket orders (Entry + SL + Target)
**FR-013:** System shall resolve instrument symbols in < 1ms
**FR-014:** System shall support multi-asset trading (Equities, F&O)
**FR-015:** System shall provide WebSocket streaming to UI

### 7.2 Non-Functional Requirements

**Performance:**
- **NFR-001:** Order latency (p95) < 50ms
- **NFR-002:** UI price rendering < 1ms
- **NFR-003:** Strategy execution < 1ms per tick
- **NFR-004:** System throughput: 10k ticks/sec sustained
- **NFR-005:** Symbol resolution < 1ms
- **NFR-006:** WebSocket reconnection < 5 seconds

**Reliability:**
- **NFR-007:** System uptime: 99.9% during market hours
- **NFR-008:** Zero data loss under normal operation
- **NFR-009:** Automatic reconnection on connection failure
- **NFR-010:** Graceful degradation under load

**Scalability:**
- **NFR-011:** Support 100+ concurrent strategies
- **NFR-012:** Handle 100k ticks/sec peak load
- **NFR-013:** Support 10k orders/minute
- **NFR-014:** Horizontal scaling capability

**Security:**
- **NFR-015:** JWT-based authentication
- **NFR-016:** API key encryption at rest
- **NFR-017:** HTTPS/WSS for all communications
- **NFR-018:** Role-based access control (RBAC)

**Maintainability:**
- **NFR-019:** Comprehensive logging (JSON structured)
- **NFR-020:** Prometheus metrics on all critical paths
- **NFR-021:** < 30 minute mean time to recovery (MTTR)
- **NFR-022:** Modular architecture for easy updates

**Usability:**
- **NFR-023:** UI shall be responsive (1920x1080 minimum)
- **NFR-024:** Keyboard shortcuts for all major actions
- **NFR-025:** Real-time visual feedback on all operations
- **NFR-026:** Zero page reloads during operation

### 7.3 Angel One SmartAPI Requirements

**Authentication:**
- API Key, Client Code, PIN, TOTP token
- Session token refresh (valid for ~6 hours)
- Feed token for WebSocket

**Rate Limits:**
- Historical data: 3 requests/second
- Order placement: 10 requests/second
- Quote/LTP: 5 requests/second
- WebSocket: No documented limit (reasonable use)

**Supported Order Types:**
- Market, Limit, Stop-Loss, Stop-Loss Market
- Product types: Intraday (MIS), Delivery (CNC), Cover Order (CO), Bracket Order (BO)

**WebSocket Modes:**
- LTP: Last Traded Price
- QUOTE: LTP + Bid/Ask + Depth
- SNAP_QUOTE: Full market depth

**Instruments:**
- NSE/BSE Equities
- NSE F&O (Futures & Options)
- Currency derivatives
- Commodities (MCX)

### 7.4 Technical Requirements

**Infrastructure:**
- Python 3.10+
- PostgreSQL 14+ (for trade history)
- Redis 7+ (for caching)
- Docker & Docker Compose
- nginx (reverse proxy)

**Libraries:**
- Nautilus Trader >= 1.195.0
- FastAPI >= 0.104.0
- SmartAPI Python SDK
- Prometheus Client
- asyncio, aiohttp, uvicorn
- pandas, numpy
- Lightweight Charts (JS)

**Development Tools:**
- pytest (testing)
- black (formatting)
- mypy (type checking)
- pre-commit hooks

---

## 8. SYSTEM LIMITATIONS

### 8.1 Broker-Imposed Limitations

**Angel One SmartAPI:**
- Rate limits (3/sec historical, 10/sec orders)
- Session timeout (~6 hours, requires refresh)
- No official API for bracket orders (need GTT workaround)
- WebSocket disconnects periodically (need reconnection)
- Scrip master updates daily (need daily download)
- Order modifications limited (some order types can't be modified)

**Mitigation Strategies:**
- Implement token bucket rate limiter
- Auto-refresh session 30 min before expiry
- Build bracket order logic on top of GTT
- Exponential backoff reconnection
- Automated daily scrip master download
- Cache order state locally

### 8.2 Performance Limitations

**Single-Process Bottlenecks:**
- Python GIL limits CPU-bound parallelism
- Single Nautilus instance per process
- WebSocket client is single-threaded

**Mitigation:**
- Use Nautilus Cython optimization for critical paths
- Run multiple TradingNode instances (different strategies)
- Use multiprocessing for CPU-heavy tasks
- Offload WebSocket to separate thread

**Network Latency:**
- India-based servers: 10-30ms to exchange
- International servers: 50-200ms
- WebSocket latency: 5-20ms

**Mitigation:**
- Host on Mumbai/Bangalore cloud (closest to NSE/BSE)
- Use CDN for UI assets
- Implement local caching
- Optimize payload sizes

### 8.3 Resource Limitations

**Memory:**
- 200k instruments: ~500MB
- Historical data (6 months, 100 symbols): ~2GB
- Nautilus cache: 100-500MB per strategy
- Total estimate: 4-8GB per instance

**CPU:**
- Strategy processing: 10-30% single core
- WebSocket handling: 5-10% single core
- FastAPI backend: 10-20% single core
- Total estimate: 2-4 cores

**Disk:**
- Historical data (Parquet): 10-50GB
- Logs (30 days retention): 5-10GB
- PostgreSQL (1 year trades): 1-5GB
- Total estimate: 20-100GB

**Network:**
- WebSocket: ~1 Mbps sustained
- REST API: ~0.5 Mbps
- UI streaming: ~0.5 Mbps per client
- Total estimate: 5-10 Mbps

### 8.4 Market Limitations

**Trading Hours:**
- NSE Equity: 9:15 AM - 3:30 PM IST
- NSE F&O: 9:15 AM - 3:30 PM IST
- Pre-market: 9:00 AM - 9:15 AM
- Post-market: 3:30 PM - 4:00 PM

**Circuit Breakers:**
- 10% up/down triggers market-wide halt
- Individual stock limits: 5%, 10%, 20%
- System must handle halts gracefully

**Liquidity:**
- Low liquidity in non-index options
- Wide bid-ask spreads in illiquid stocks
- Slippage can exceed backtested expectations

**Mitigation:**
- Operate only during market hours
- Implement circuit breaker detection
- Filter strategies to liquid instruments only
- Add slippage models to backtests

### 8.5 Regulatory Limitations

**SEBI Regulations:**
- No naked short selling in equity
- Margin requirements change dynamically
- Algo trading requires broker approval
- Position limits on F&O contracts

**Compliance:**
- Maintain audit trail for 5 years
- Report suspicious trading patterns
- Adhere to broker's algo trading policy
- Register as algo trader if required

---

## 9. DEPLOYMENT STRATEGY

### 9.1 Local Development

```bash
# 1. Clone repository
git clone <repo-url>
cd trading-platform

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with Angel One credentials

# 5. Download scrip master
python scripts/download_instruments.py

# 6. Run backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 7. Open UI
# Navigate to http://localhost:8000/ui/
```

### 9.2 Docker Deployment

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  # Trading backend (FastAPI + Nautilus)
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: trading-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ANGEL_API_KEY=${ANGEL_API_KEY}
      - ANGEL_CLIENT_CODE=${ANGEL_CLIENT_CODE}
      - ANGEL_PASSWORD=${ANGEL_PASSWORD}
      - ANGEL_TOTP_TOKEN=${ANGEL_TOTP_TOKEN}
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/trading
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
    depends_on:
      - postgres
      - redis
    networks:
      - trading-network

  # PostgreSQL database
  postgres:
    image: postgres:15-alpine
    container_name: trading-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=trading
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - trading-network

  # Redis cache
  redis:
    image: redis:7-alpine
    container_name: trading-redis
    restart: unless-stopped
    networks:
      - trading-network

  # Prometheus metrics
  prometheus:
    image: prom/prometheus:latest
    container_name: trading-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/rules:/etc/prometheus/rules
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
    networks:
      - trading-network

  # Grafana dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: trading-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_INSTALL_PLUGINS=
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - trading-network

  # nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: trading-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./src/ui:/usr/share/nginx/html/ui
    depends_on:
      - backend
    networks:
      - trading-network

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  trading-network:
    driver: bridge
```

**Start entire stack:**

```bash
docker-compose up -d
```

### 9.3 Production Deployment (AWS/GCP/Azure)

**Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│              Load Balancer (ALB/GCP LB)                 │
│              - SSL termination                          │
│              - Health checks                            │
└────────────┬──────────────────┬─────────────────────────┘
             │                  │
     ┌───────▼────────┐  ┌──────▼──────────┐
     │  Web Server    │  │  Web Server     │
     │  (nginx)       │  │  (nginx)        │
     └───────┬────────┘  └──────┬──────────┘
             │                  │
     ┌───────▼──────────────────▼──────────┐
     │  Trading Backend (Auto-scaling)     │
     │  - FastAPI                          │
     │  - Nautilus TradingNode             │
     │  - Min: 2 instances                 │
     │  - Max: 10 instances                │
     └───────┬─────────────────────────────┘
             │
     ┌───────▼──────────────────────────────┐
     │  Managed Services                    │
     │  - RDS PostgreSQL (Multi-AZ)         │
     │  - ElastiCache Redis (Cluster)       │
     │  - S3 (Data storage)                 │
     │  - CloudWatch (Monitoring)           │
     └──────────────────────────────────────┘
```

**Deployment Steps:**

1. **Provision Infrastructure (Terraform)**
   ```bash
   cd terraform/
   terraform init
   terraform plan
   terraform apply
   ```

2. **Build Docker Image**
   ```bash
   docker build -t trading-platform:v1.0 .
   docker tag trading-platform:v1.0 <registry>/trading-platform:v1.0
   docker push <registry>/trading-platform:v1.0
   ```

3. **Deploy to Kubernetes (EKS/GKE)**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

4. **Configure Monitoring**
   ```bash
   helm install prometheus prometheus-community/kube-prometheus-stack
   helm install grafana grafana/grafana
   ```

5. **Set Up CI/CD (GitHub Actions)**
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy
   on:
     push:
       branches: [main]
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Build & Push
           run: |
             docker build -t trading-platform:${{ github.sha }} .
             docker push <registry>/trading-platform:${{ github.sha }}
         - name: Deploy to K8s
           run: |
             kubectl set image deployment/trading-backend \
               backend=<registry>/trading-platform:${{ github.sha }}
   ```

### 9.4 Production Hardening Checklist

- [ ] Enable HTTPS/WSS only (no HTTP)
- [ ] Implement rate limiting on API endpoints
- [ ] Set up WAF (Web Application Firewall)
- [ ] Enable database encryption at rest
- [ ] Implement secret management (AWS Secrets Manager/Vault)
- [ ] Set up automated backups (daily)
- [ ] Configure log rotation and archival
- [ ] Implement DDoS protection
- [ ] Set up intrusion detection (IDS)
- [ ] Enable audit logging for all trades
- [ ] Implement API key rotation policy
- [ ] Set up disaster recovery runbook
- [ ] Configure auto-scaling policies
- [ ] Set up health check endpoints
- [ ] Implement circuit breakers
- [ ] Enable request tracing (distributed tracing)
- [ ] Set up alerting (PagerDuty/Opsgenie)
- [ ] Conduct penetration testing
- [ ] Review security headers
- [ ] Implement RBAC (Role-Based Access Control)

---

## 10. SCALABILITY ROADMAP (10X LOAD PLAN)

### 10.1 Current Baseline (1x Load)

**Assumptions:**
- 10 concurrent strategies
- 10k ticks/second
- 1k orders/minute
- 10 concurrent UI clients

**Resource Usage:**
- CPU: 2-4 cores
- Memory: 4-8GB
- Network: 5-10 Mbps
- Disk I/O: 10-20 MB/s

### 10.2 Target Scale (10x Load)

**Requirements:**
- 100 concurrent strategies
- 100k ticks/second
- 10k orders/minute
- 100 concurrent UI clients

**Challenges:**
1. Bridge queue overflow
2. Database write bottleneck
3. WebSocket connection limits
4. Memory exhaustion
5. CPU saturation

### 10.3 Scaling Strategies

**Horizontal Scaling:**

```
┌────────────────────────────────────────────┐
│         Load Balancer                      │
└─────┬──────────┬──────────┬────────────┬───┘
      │          │          │            │
┌─────▼────┐ ┌──▼─────┐ ┌──▼─────┐ ┌───▼──────┐
│ Backend  │ │Backend │ │Backend │ │ Backend  │
│ Instance │ │Instance│ │Instance│ │ Instance │
│ 1-25     │ │26-50   │ │51-75   │ │ 76-100   │
│strategies│ │strat.  │ │strat.  │ │ strat.   │
└──────────┘ └────────┘ └────────┘ └──────────┘
      │          │          │            │
      └──────────┴──────────┴────────────┘
                    │
            ┌───────▼────────┐
            │ Shared Services│
            │ - PostgreSQL   │
            │ - Redis Cluster│
            │ - Kafka        │
            └────────────────┘
```

**1. Database Optimization**
- Implement connection pooling (500+ connections)
- Add database replicas (read-only)
- Partition tables by date/symbol
- Use TimescaleDB for time-series data
- Implement write batching (bulk inserts)
- Add caching layer (Redis)

**2. Message Queue Introduction**
- Replace direct database writes with Kafka/RabbitMQ
- Async event processing
- Decouple write path from read path
- Implement event sourcing for audit trail

**3. Data Bridge Optimization**
- Increase queue size (10k → 100k)
- Implement multiple Bridge instances (sharding by symbol)
- Use lock-free queues (multiprocessing.Queue → queue.Queue)
- Add tick aggregation (reduce granularity where acceptable)

**4. WebSocket Scaling**
- Implement WebSocket gateway (separate from backend)
- Use Redis Pub/Sub for broadcast
- Add CDN for static assets
- Implement WebSocket connection pooling

**5. Strategy Distribution**
- Shard strategies across instances by symbol
- Use consistent hashing for assignment
- Implement strategy orchestrator (Kubernetes CronJob)
- Add strategy health monitoring

**6. Caching Strategy**
- Multi-layer caching (L1: in-memory, L2: Redis, L3: DB)
- Cache instrument data (TTL: 24 hours)
- Cache market data (TTL: 1 second)
- Implement cache warming on startup

**7. Resource Optimization**
- Use Cython for critical paths (already in Nautilus)
- Implement object pooling (reduce GC pressure)
- Use numpy for bulk calculations
- Profile and optimize hot paths
- Consider Rust for ultra-low-latency components

### 10.4 Infrastructure Scaling Plan

**Phase 1: Vertical Scaling (2x-3x)**
- Upgrade to larger instances (8 cores, 16GB RAM)
- Use faster disks (NVMe SSD)
- Optimize database (more connections, better indices)
- **Cost**: +50%

**Phase 2: Horizontal Scaling (3x-5x)**
- Add 2-3 backend instances
- Implement load balancer
- Set up database replication
- Add Redis cluster
- **Cost**: +100%

**Phase 3: Distributed Architecture (5x-10x)**
- Introduce message queue (Kafka)
- Separate WebSocket gateway
- Implement CDN
- Add database sharding
- Use microservices architecture
- **Cost**: +200%

### 10.5 Performance Targets at 10x Scale

| Metric | 1x Load | 10x Load | Strategy |
|--------|---------|----------|----------|
| Order Latency (p95) | 50ms | 100ms | Horizontal scaling, caching |
| UI Render | 1ms | 2ms | CDN, WebSocket gateway |
| Strategy Execution | 1ms | 2ms | Sharding, optimization |
| Throughput (ticks/sec) | 10k | 100k | Multiple Bridge instances |
| Concurrent Strategies | 10 | 100 | Distributed deployment |
| Memory per instance | 8GB | 16GB | Optimization, pooling |
| CPU per instance | 4 cores | 8 cores | Optimization, Cython |

### 10.6 Cost Estimation

**Current (1x):** ~$500/month
- 1x backend server (4 cores, 8GB): $100
- PostgreSQL RDS: $150
- Redis: $50
- Monitoring: $50
- Network: $50
- Storage: $100

**Target (10x):** ~$2,500/month
- 4x backend servers (8 cores, 16GB each): $800
- PostgreSQL RDS (Multi-AZ, replicas): $600
- Redis Cluster: $300
- Kafka: $200
- Monitoring: $200
- Network: $200
- Storage: $200

**Cost Optimization:**
- Use reserved instances (30-50% savings)
- Implement auto-scaling (scale down during off-hours)
- Use spot instances for non-critical workloads
- Optimize storage (S3 Glacier for old data)

---

## 11. ANGEL ONE SMARTAPI INTEGRATION GUIDE

### 11.1 Authentication Flow

```python
# adapters/angel/auth.py
from SmartApi import SmartConnect
import pyotp
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class AngelAuthManager:
    """Manages Angel One authentication and session"""
    
    def __init__(self, api_key: str, client_code: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_code = client_code
        self.password = password
        self.totp_secret = totp_secret
        self.client = SmartConnect(api_key=api_key)
        self.session_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.session_expiry: Optional[datetime] = None
    
    def generate_totp(self) -> str:
        """Generate TOTP token"""
        totp = pyotp.TOTP(self.totp_secret)
        return totp.now()
    
    def login(self) -> bool:
        """Perform login and get session tokens"""
        try:
            totp_token = self.generate_totp()
            
            data = self.client.generateSession(
                clientCode=self.client_code,
                password=self.password,
                totp=totp_token
            )
            
            if data['status']:
                self.session_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                self.refresh_token = data['data']['refreshToken']
                self.session_expiry = datetime.now() + timedelta(hours=6)
                
                logger.info("Angel One login successful")
                return True
            else:
                logger.error(f"Login failed: {data.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Login exception: {e}")
            return False
    
    def refresh_session(self) -> bool:
        """Refresh session token"""
        try:
            data = self.client.renewAccessToken(self.refresh_token)
            
            if data['status']:
                self.session_token = data['data']['jwtToken']
                self.feed_token = data['data']['feedToken']
                self.session_expiry = datetime.now() + timedelta(hours=6)
                logger.info("Session refreshed successfully")
                return True
            else:
                logger.error(f"Session refresh failed: {data.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Session refresh exception: {e}")
            return False
    
    def is_session_valid(self) -> bool:
        """Check if current session is valid"""
        if not self.session_token:
            return False
        
        # Refresh if expiring within 30 minutes
        if self.session_expiry and \
           self.session_expiry - datetime.now() < timedelta(minutes=30):
            return self.refresh_session()
        
        return True
    
    def ensure_authenticated(self):
        """Ensure valid authentication"""
        if not self.is_session_valid():
            return self.login()
        return True
```

### 11.2 WebSocket Implementation

```python
# adapters/angel/websocket_client.py
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from typing import Callable, Set
import logging
import threading

logger = logging.getLogger(__name__)

class AngelWebSocketClient:
    """Angel One WebSocket V2 client"""
    
    # Subscription modes
    MODE_LTP = 1
    MODE_QUOTE = 2
    MODE_SNAP_QUOTE = 3
    
    def __init__(
        self,
        auth_manager: AngelAuthManager,
        on_tick: Callable,
        on_connect: Callable = None,
        on_close: Callable = None,
        on_error: Callable = None,
    ):
        self.auth = auth_manager
        self.on_tick_callback = on_tick
        self.on_connect_callback = on_connect
        self.on_close_callback = on_close
        self.on_error_callback = on_error
        
        self.ws = None
        self.subscribed_tokens: Set[str] = set()
        self.correlation_id = "trading_platform"
        self.thread = None
        self.running = False
    
    def connect(self):
        """Connect to WebSocket"""
        if not self.auth.ensure_authenticated():
            raise Exception("Authentication failed")
        
        self.ws = SmartWebSocketV2(
            auth_token=self.auth.session_token,
            api_key=self.auth.api_key,
            client_code=self.auth.client_code,
            feed_token=self.auth.feed_token,
        )
        
        self.ws.on_open = self._on_open
        self.ws.on_data = self._on_data
        self.ws.on_error = self._on_error
        self.ws.on_close = self._on_close
        
        # Start WebSocket in separate thread
        self.running = True
        self.thread = threading.Thread(target=self.ws.connect)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info("WebSocket connection initiated")
    
    def disconnect(self):
        """Disconnect WebSocket"""
        self.running = False
        if self.ws:
            self.ws.close_connection()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("WebSocket disconnected")
    
    def subscribe(self, token: str, mode: int = MODE_QUOTE):
        """Subscribe to instrument"""
        if token not in self.subscribed_tokens:
            self.ws.subscribe(self.correlation_id, mode, [token])
            self.subscribed_tokens.add(token)
            logger.info(f"Subscribed to {token}")
    
    def unsubscribe(self, token: str, mode: int = MODE_QUOTE):
        """Unsubscribe from instrument"""
        if token in self.subscribed_tokens:
            self.ws.unsubscribe(self.correlation_id, mode, [token])
            self.subscribed_tokens.discard(token)
            logger.info(f"Unsubscribed from {token}")
    
    def _on_open(self, ws):
        """WebSocket opened"""
        logger.info("WebSocket opened")
        if self.on_connect_callback:
            self.on_connect_callback()
    
    def _on_data(self, ws, message):
        """Received WebSocket data"""
        try:
            # Call user callback with tick data
            self.on_tick_callback(message)
        except Exception as e:
            logger.error(f"Error in tick callback: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket error"""
        logger.error(f"WebSocket error: {error}")
        if self.on_error_callback:
            self.on_error_callback(error)
    
    def _on_close(self, ws):
        """WebSocket closed"""
        logger.info("WebSocket closed")
        if self.on_close_callback:
            self.on_close_callback()
        
        # Auto-reconnect if still running
        if self.running:
            logger.info("Attempting to reconnect in 5 seconds...")
            threading.Timer(5.0, self.connect).start()
```

### 11.3 Sample Integration

```python
# Example usage
from src.adapters.angel import AngelAuthManager, AngelWebSocketClient
from src.bridge import DataBridge

# Initialize authentication
auth = AngelAuthManager(
    api_key="your_api_key",
    client_code="your_client_code",
    password="your_pin",
    totp_secret="your_totp_secret"
)

# Login
auth.login()

# Initialize data bridge
bridge = DataBridge()

# Create WebSocket client
ws_client = AngelWebSocketClient(
    auth_manager=auth,
    on_tick=bridge.submit_tick,  # Submit ticks to bridge
)

# Connect
ws_client.connect()

# Subscribe to instruments
ws_client.subscribe(token="99926000", mode=AngelWebSocketClient.MODE_QUOTE)  # NIFTY 50
ws_client.subscribe(token="99926009", mode=AngelWebSocketClient.MODE_QUOTE)  # BANKNIFTY

# System is now streaming live data!
```

---

## 12. CONCLUSION

This document provides a comprehensive blueprint for building an institutional-grade hybrid algorithmic trading ecosystem. The architecture balances performance, reliability, and maintainability while remaining pragmatic about implementation constraints.

**Key Takeaways:**

1. **Modular Design**: Clean separation between trading engine, backend, frontend, and infrastructure
2. **Event-Driven**: Asynchronous, non-blocking architecture throughout
3. **Production-First**: Built for 24/7 operation with comprehensive observability
4. **Scalable**: Clear path from 1x to 10x load
5. **Pragmatic**: Acknowledges limitations and provides mitigation strategies

**Next Steps:**

1. Review this architecture with team
2. Set up development environment
3. Begin Phase 1 implementation (Foundation)
4. Iterate based on real-world performance
5. Scale incrementally as needed

**Success Metrics:**

- Order latency < 50ms (p95)
- System uptime > 99.9%
- Zero data loss
- < 30 min MTTR
- Profitable strategies (the ultimate metric!)

---

**END OF DOCUMENT**
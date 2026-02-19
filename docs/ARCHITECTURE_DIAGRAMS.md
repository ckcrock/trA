# SYSTEM ARCHITECTURE DIAGRAMS
## Hybrid Algorithmic Trading Ecosystem

---

## 1. COMPLETE SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CLIENT TIER                                           │
│                                                                                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────────────────┐   │
│  │   Web Terminal      │  │   Mobile App        │  │   External Trading Tools     │   │
│  │   (Vanilla JS)      │  │   (Future)          │  │   (TradingView, etc.)        │   │
│  │                     │  │                     │  │                                │   │
│  │ • Price Charts      │  │ • Order Placement   │  │ • Webhooks                     │   │
│  │ • Order Panel       │  │ • Portfolio View    │  │ • API Integration              │   │
│  │ • Positions Panel   │  │ • Alerts            │  │ • Strategy Signals             │   │
│  │ • Heatmaps          │  │                     │  │                                │   │
│  └──────────┬──────────┘  └──────────┬──────────┘  └─────────────┬──────────────────┘   │
└─────────────┼──────────────────────────┼─────────────────────────┼──────────────────────┘
              │                          │                         │
              │ WebSocket                │ REST API                │ Webhooks
              │ (WSS)                    │ (HTTPS)                 │ (HTTPS)
              │                          │                         │
┌─────────────▼──────────────────────────▼─────────────────────────▼──────────────────────┐
│                              APPLICATION TIER                                            │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           FastAPI Backend (Port 8000)                              │ │
│  │                                                                                    │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────────┐  │ │
│  │  │  REST Routes     │  │  WebSocket Hub   │  │  Background Task Manager       │  │ │
│  │  │                  │  │                  │  │                                │  │ │
│  │  │ /api/orders      │  │ • Price feed     │  │ • Order reconciliation (30s)   │  │ │
│  │  │ /api/positions   │  │ • Order updates  │  │ • Position sync (60s)          │  │ │
│  │  │ /api/strategies  │  │ • Events         │  │ • Health checks (10s)          │  │ │
│  │  │ /api/market      │  │ • Broadcasts     │  │ • Session refresh (5m)         │  │ │
│  │  │ /metrics         │  │                  │  │ • Auto-reconnect logic         │  │ │
│  │  └──────────────────┘  └──────────────────┘  └────────────────────────────────┘  │ │
│  │                                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐│ │
│  │  │                      Service Layer (Dependency Injection)                    ││ │
│  │  │                                                                              ││ │
│  │  │  • StrategyService       • PortfolioService       • OrderService           ││ │
│  │  │  • MarketDataService     • RiskService            • AuthService            ││ │
│  │  └──────────────────────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                        THE BRIDGE (Real-Time Data Bus)                             │ │
│  │                                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐│ │
│  │  │  Event Normalizer & Router                                                   ││ │
│  │  │                                                                              ││ │
│  │  │  [WebSocket Tick] ──> [asyncio.Queue(10k)] ──> [Normalize] ──> [Fanout]    ││ │
│  │  │                             │                                    │          ││ │
│  │  │                             │ Backpressure                       │          ││ │
│  │  │                             ▼ Monitoring                         │          ││ │
│  │  │                     [Drop if full]                               │          ││ │
│  │  │                     [Log metrics]                                │          ││ │
│  │  │                                                                  │          ││ │
│  │  │                                                   ┌──────────────▼────────┐ ││ │
│  │  │                                                   │ Broadcast to:         │ ││ │
│  │  │                                                   │ 1. Nautilus Event Bus │ ││ │
│  │  │                                                   │ 2. WebSocket Clients  │ ││ │
│  │  │                                                   │ 3. Metrics Collector  │ ││ │
│  │  │                                                   └───────────────────────┘ ││ │
│  │  └──────────────────────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬──────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────────────────┐
│                              EXECUTION TIER                                              │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    NAUTILUS TRADER CORE ENGINE                                     │ │
│  │                                                                                    │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────────┐   │ │
│  │  │  TradingNode    │  │  DataEngine     │  │  ExecutionEngine                │   │ │
│  │  │                 │  │                 │  │                                 │   │ │
│  │  │ • Strategy Mgmt │  │ • Cache         │  │ • Order state machine           │   │ │
│  │  │ • Event Bus     │  │ • Catalog       │  │ • Fill processing               │   │ │
│  │  │ • Hot-swap      │  │ • Ticks/Bars    │  │ • Risk validation               │   │ │
│  │  │ • Lifecycle     │  │ • Aggregation   │  │ • Position management           │   │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────────────────┘   │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │                         ACTIVE STRATEGIES                                  │   │ │
│  │  │                                                                            │   │ │
│  │  │  Strategy 1: EMA Cross    │  Strategy 2: RSI Break  │  Strategy N: ...   │   │ │
│  │  │  • on_quote_tick()        │  • on_bar()             │  • Custom logic    │   │ │
│  │  │  • calculate_signals()    │  • risk_sizing()        │  • Event-driven    │   │ │
│  │  │  • place_orders()         │  • place_orders()       │                    │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    MANUAL EXECUTION ENGINE (Parallel Operation)                    │ │
│  │                                                                                    │ │
│  │  ┌──────────────────────┐  ┌──────────────────────┐  ┌───────────────────────┐   │ │
│  │  │ PaperPortfolio       │  │ GTT Order Manager    │  │ Bracket Order Manager │   │ │
│  │  │ Engine               │  │                      │  │                       │   │ │
│  │  │                      │  │ • Trigger detection  │  │ • Entry + SL + Target │   │ │
│  │  │ • Virtual positions  │  │ • Auto-execution     │  │ • Auto-management     │   │ │
│  │  │ • P&L tracking       │  │ • Status tracking    │  │ • Risk controls       │   │ │
│  │  │ • Risk validation    │  │                      │  │                       │   │ │
│  │  └──────────────────────┘  └──────────────────────┘  └───────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬──────────────────────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────────────────┐
│                              ADAPTER TIER                                                │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    ANGEL ONE / SMARTAPI ADAPTERS                                   │ │
│  │                                                                                    │ │
│  │  ┌──────────────────────────────┐  ┌───────────────────────────────────────────┐ │ │
│  │  │  DataClient                  │  │  ExecutionClient                          │ │ │
│  │  │                              │  │                                           │ │ │
│  │  │ • Historical data fetch      │  │ • Order placement (Market/Limit/SL)       │ │ │
│  │  │ • Live WebSocket streaming   │  │ • Order modification                      │ │ │
│  │  │ • Tick normalization         │  │ • Order cancellation                      │ │ │
│  │  │ • Reconnection logic         │  │ • Status sync                             │ │ │
│  │  │ • Rate limiting (3 req/sec)  │  │ • Rate limiting (10 req/sec)              │ │ │
│  │  └──────────────────────────────┘  └───────────────────────────────────────────┘ │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │  InstrumentCatalog (SymbolResolver)                                        │   │ │
│  │  │                                                                            │   │ │
│  │  │  • 200k+ instruments in-memory                                            │   │ │
│  │  │  • Multi-index: Symbol / Token / Expiry / Exchange                        │   │ │
│  │  │  • <1ms lookup time                                                       │   │ │
│  │  │  • Daily CSV refresh                                                      │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  │                                                                                    │ │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐   │ │
│  │  │  Rate Limiter (Token Bucket)                                               │   │ │
│  │  │                                                                            │   │ │
│  │  │  Historical: 3 req/sec  │  Orders: 10 req/sec  │  Quotes: 5 req/sec      │   │ │
│  │  │  Thread-safe            │  Async-compatible     │  Backoff on limit       │   │ │
│  │  └────────────────────────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬──────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/REST + WebSocket V2
                                    │
┌───────────────────────────────────▼──────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                                           │
│                                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │  Angel One           │  │  NSE/BSE Exchanges   │  │  Market Data Providers       │  │
│  │  SmartAPI            │  │                      │  │                              │  │
│  │                      │  │  • Order matching    │  │  • Alternative data          │  │
│  │  • Authentication    │  │  • Trade execution   │  │  • News feeds                │  │
│  │  • Order routing     │  │  • Settlement        │  │  • Fundamental data          │  │
│  │  • Market data       │  │  • Regulatory        │  │                              │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                       OBSERVABILITY TIER (Cross-Cutting)                                 │
│                                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │  Prometheus          │  │  Grafana             │  │  Structured Logging          │  │
│  │  (Port 9090)         │  │  (Port 3000)         │  │                              │  │
│  │                      │  │                      │  │  • JSON format               │  │
│  │  • Metrics scraping  │  │  • Dashboards        │  │  • Log levels                │  │
│  │  • Time-series DB    │  │  • Alerts            │  │  • Trace IDs                 │  │
│  │  • Alert rules       │  │  • Visualizations    │  │  • Rotation/archival         │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA STORAGE TIER                                           │
│                                                                                          │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │  PostgreSQL          │  │  Redis               │  │  Parquet Files               │  │
│  │  (Port 5432)         │  │  (Port 6379)         │  │  (Local/S3)                  │  │
│  │                      │  │                      │  │                              │  │
│  │  • Trade history     │  │  • Session cache     │  │  • Historical bars           │  │
│  │  • Order log         │  │  • Instrument cache  │  │  • Tick data                 │  │
│  │  • Performance stats │  │  • Real-time state   │  │  • Backtest data             │  │
│  │  • Audit trail       │  │  • Pub/Sub           │  │  • Nautilus catalog          │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. DATA FLOW DIAGRAM

### 2.1 Market Data Flow (Real-Time)

```
┌──────────────────────────────────────────────────────────────────────┐
│  MARKET DATA INGESTION PIPELINE                                      │
└──────────────────────────────────────────────────────────────────────┘

Step 1: WebSocket Receive (Thread-based)
┌──────────────────────┐
│ Angel WebSocket      │
│ Feed (Thread)        │
│                      │
│ Tick arrives:        │
│ {                    │
│   symbol: "SBIN",    │
│   ltp: 720.50,       │
│   volume: 1234,      │
│   timestamp: ...     │
│ }                    │
└──────────┬───────────┘
           │ (5ms)
           │
Step 2: Submit to Bridge
           │
           ▼
┌──────────────────────┐
│ DataBridge           │
│ Thread-safe submit   │
│                      │
│ queue.put_nowait(    │
│   tick_data          │
│ )                    │
└──────────┬───────────┘
           │ (1ms)
           │
Step 3: Async Processing
           │
           ▼
┌──────────────────────┐
│ Bridge Event Loop    │
│                      │
│ tick = await         │
│   queue.get()        │
│                      │
│ normalized = {       │
│   symbol, ltp,       │
│   bid, ask, ...      │
│ }                    │
└──────────┬───────────┘
           │ (2ms)
           │
Step 4: Fanout Broadcast
           │
           ├──────────────────────┐
           │                      │
           ▼                      ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Nautilus Event Bus   │  │ WebSocket Clients    │
│                      │  │                      │
│ QuoteTick created    │  │ JSON.stringify(tick) │
│ -> Strategies        │  │ -> UI clients        │
│ -> DataEngine        │  │                      │
└──────────┬───────────┘  └──────────┬───────────┘
           │ (3ms)                   │ (1ms)
           │                         │
Step 5: Processing               Step 5: Rendering
           │                         │
           ▼                         ▼
┌──────────────────────┐  ┌──────────────────────┐
│ Strategy.on_tick()   │  │ Chart.update()       │
│ • Calculate signals  │  │ • DOM update         │
│ • Risk checks        │  │ • Price animation    │
│ • Place orders       │  │                      │
└──────────────────────┘  └──────────────────────┘

TOTAL LATENCY: ~12ms (WebSocket receive to UI render)
```

### 2.2 Order Execution Flow (Full Cycle)

```
┌──────────────────────────────────────────────────────────────────────┐
│  ORDER EXECUTION PIPELINE                                            │
└──────────────────────────────────────────────────────────────────────┘

Step 1: Order Initiation
┌──────────────────────┐
│ Strategy / UI        │
│                      │
│ Order Request:       │
│ {                    │
│   symbol: "SBIN",    │
│   side: "BUY",       │
│   qty: 100,          │
│   type: "LIMIT",     │
│   price: 720.00      │
│ }                    │
└──────────┬───────────┘
           │
           ▼
Step 2: Validation
┌──────────────────────┐
│ OrderService         │
│                      │
│ • Schema validation  │
│ • Symbol lookup      │
│ • Quantity check     │
│ • Price validation   │
└──────────┬───────────┘
           │ (2ms)
           │
Step 3: Risk Checks
           │
           ▼
┌──────────────────────┐
│ RiskEngine           │
│                      │
│ • Position limit     │
│ • Margin check       │
│ • Drawdown limit     │
│ • Exposure check     │
└──────────┬───────────┘
           │ (3ms)
           │
Step 4: Rate Limiting
           │
           ▼
┌──────────────────────┐
│ RateLimiter          │
│                      │
│ await limiter        │
│   .acquire_async()   │
│                      │
│ (Waits if needed)    │
└──────────┬───────────┘
           │ (0-500ms)
           │
Step 5: API Call
           │
           ▼
┌──────────────────────┐
│ ExecutionClient      │
│                      │
│ response = await     │
│   client.placeOrder( │
│     params           │
│   )                  │
└──────────┬───────────┘
           │ (20-50ms network)
           │
Step 6: Broker Processing
           │
           ▼
┌──────────────────────┐
│ Angel SmartAPI       │
│                      │
│ • Validate order     │
│ • Check RMS          │
│ • Route to exchange  │
└──────────┬───────────┘
           │ (5-10ms)
           │
Step 7: Exchange Matching
           │
           ▼
┌──────────────────────┐
│ NSE/BSE Exchange     │
│                      │
│ • Order book match   │
│ • Generate trade     │
│ • Send confirmation  │
└──────────┬───────────┘
           │ (1-5ms)
           │
Step 8: Fill Notification
           │
           ▼
┌──────────────────────┐
│ WebSocket Callback   │
│                      │
│ Fill event:          │
│ {                    │
│   order_id: "...",   │
│   status: "COMPLETE",│
│   filled_qty: 100    │
│ }                    │
└──────────┬───────────┘
           │ (5-10ms)
           │
Step 9: Position Update
           │
           ▼
┌──────────────────────┐
│ PortfolioEngine      │
│                      │
│ • Update position    │
│ • Calculate P&L      │
│ • Update margin      │
│ • Notify strategy    │
└──────────┬───────────┘
           │ (2ms)
           │
Step 10: UI Broadcast
           │
           ▼
┌──────────────────────┐
│ WebSocket Broadcast  │
│                      │
│ • Positions updated  │
│ • Order status       │
│ • P&L refresh        │
└──────────────────────┘

TOTAL LATENCY: 40-90ms (Order placement to confirmation)
P95 TARGET: <50ms
```

---

## 3. DEPLOYMENT ARCHITECTURE

### 3.1 Production Deployment (Cloud)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                       │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ HTTPS/WSS
                                │
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                     Application Load Balancer                               │
│                     • SSL Termination (TLS 1.3)                             │
│                     • Health Checks (/health)                               │
│                     • Path-based routing                                    │
│                     • Rate limiting (10k req/min)                           │
└─────┬──────────────────────────────────┬────────────────────────────────────┘
      │                                  │
      │ /api/*                           │ /ui/*
      │                                  │
┌─────▼──────────────────────┐    ┌──────▼─────────────────────┐
│  Backend Instances         │    │  Static Assets (CDN/S3)    │
│  (Auto-scaling 2-10)       │    │                            │
│                            │    │  • index.html              │
│  • FastAPI                 │    │  • CSS/JS files            │
│  • Nautilus Engine         │    │  • Images/fonts            │
│  • DataBridge              │    │                            │
│  • Adapters                │    │  CloudFront (optional)     │
└─────┬──────────────────────┘    └────────────────────────────┘
      │
      │ Database connections
      │
┌─────▼────────────────────────────────────────────────────────────────┐
│                    Data Layer (Managed Services)                     │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ RDS PostgreSQL   │  │ ElastiCache Redis│  │ S3 Storage       │  │
│  │ (Multi-AZ)       │  │ (Cluster mode)   │  │                  │  │
│  │                  │  │                  │  │ • Parquet files  │  │
│  │ • Read replicas  │  │ • 3 nodes        │  │ • Backups        │  │
│  │ • Auto backup    │  │ • Failover       │  │ • Logs archive   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    Monitoring & Observability                        │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ CloudWatch       │  │ Prometheus       │  │ Grafana          │  │
│  │ • Logs           │  │ (Managed)        │  │ (Managed)        │  │
│  │ • Metrics        │  │                  │  │                  │  │
│  │ • Alarms         │  │ • Custom metrics │  │ • Dashboards     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 High Availability Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                    Availability Zone 1                          │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ Backend Pod 1 │  │ Backend Pod 2 │  │ Postgres Primary │   │
│  │               │  │               │  │                  │   │
│  │ Strategy 1-25 │  │ Strategy26-50 │  │ (Read/Write)     │   │
│  └───────────────┘  └───────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Replication
                            │
┌─────────────────────────────────────────────────────────────────┐
│                    Availability Zone 2                          │
│                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────┐   │
│  │ Backend Pod 3 │  │ Backend Pod 4 │  │ Postgres Standby │   │
│  │               │  │               │  │                  │   │
│  │ Strategy51-75 │  │ Strategy76-100│  │ (Read-only)      │   │
│  └───────────────┘  └───────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Failover Strategy:
- Automatic failover in <30 seconds
- Health checks every 10 seconds
- Rolling updates (zero downtime)
- Database replication lag <1 second
```

---

## 4. COMPONENT INTERACTION DIAGRAM

### 4.1 Strategy Hot-Swap Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                  STRATEGY HOT-SWAP SEQUENCE                      │
└──────────────────────────────────────────────────────────────────┘

Time ─────────────────────────────────────────────────────────>

T0: Request received
┌────────────┐
│ API /swap  │
└──────┬─────┘
       │
       ▼
T1: Load new strategy (1s)
┌────────────────────┐
│ Import module      │
│ Validate config    │
│ Initialize instance│
└──────┬─────────────┘
       │
       ▼
T2: Pause old strategy (0.5s)
┌────────────────────┐
│ Stop new orders    │
│ Wait for pending   │
│ Export state       │
└──────┬─────────────┘
       │
       ▼
T3: Transfer state (1s)
┌────────────────────┐
│ Positions          │
│ Indicators         │
│ Configuration      │
└──────┬─────────────┘
       │
       ▼
T4: Switch (0.5s)
┌────────────────────┐
│ Unregister old     │
│ Register new       │
│ Resume events      │
└──────┬─────────────┘
       │
       ▼
T5: Cleanup (2s)
┌────────────────────┐
│ Stop old gracefully│
│ Archive logs       │
│ Free memory        │
└────────────────────┘

TOTAL TIME: ~5 seconds
DOWNTIME: <1 second (during switch)
```

### 4.2 Backpressure Handling

```
┌──────────────────────────────────────────────────────────────────┐
│              BRIDGE BACKPRESSURE MANAGEMENT                      │
└──────────────────────────────────────────────────────────────────┘

Normal Operation (Queue < 80%)
┌──────────┐     ┌─────────────┐     ┌──────────┐
│ WebSocket├────>│ Queue       ├────>│ Consumers│
│ Thread   │     │ (8k/10k)    │     │          │
└──────────┘     └─────────────┘     └──────────┘
                 Process: 100%
                 Latency: 2ms

Warning State (Queue 80-95%)
┌──────────┐     ┌─────────────┐     ┌──────────┐
│ WebSocket├────>│ Queue       ├────>│ Consumers│
│ Thread   │     │ (9.5k/10k)  │     │ +Priority│
└──────────┘     └─────────────┘     └──────────┘
                 Process: 100%
                 Latency: 5ms
                 Alert: Warning

Critical State (Queue > 95%)
┌──────────┐     ┌─────────────┐     ┌──────────┐
│ WebSocket│  X  │ Queue FULL  ├────>│ Consumers│
│ Thread   │     │ (10k/10k)   │     │ +Priority│
└──────────┘     └─────────────┘     └──────────┘
                 Process: Drop new
                 Latency: 10ms+
                 Alert: CRITICAL
                 
Recovery Actions:
1. Drop non-critical ticks
2. Sample data (every Nth tick)
3. Increase consumer threads
4. Alert operations team
```

---

## 5. SCALABILITY EVOLUTION

### 5.1 Phase 1: Single Instance (1x Load)

```
┌────────────────────────────────────────┐
│  Single Server                         │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  All Components                  │ │
│  │                                  │ │
│  │  • FastAPI                       │ │
│  │  • Nautilus                      │ │
│  │  • DataBridge                    │ │
│  │  • Strategies (10)               │ │
│  │  • PostgreSQL                    │ │
│  │  • Redis                         │ │
│  └──────────────────────────────────┘ │
│                                        │
│  Resources:                            │
│  • 4 CPU cores                         │
│  • 8GB RAM                             │
│  • 100GB SSD                           │
└────────────────────────────────────────┘

Capacity: 10k ticks/sec, 1k orders/min
```

### 5.2 Phase 2: Service Separation (3x Load)

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Backend Server   │  │ Database Server  │  │ Cache Server     │
│                  │  │                  │  │                  │
│ • FastAPI        │  │ • PostgreSQL     │  │ • Redis          │
│ • Nautilus       │  │ • Optimized      │  │ • Cluster (3)    │
│ • DataBridge     │  │ • Replicas       │  │                  │
│ • Strategies(30) │  │                  │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘

Capacity: 30k ticks/sec, 3k orders/min
```

### 5.3 Phase 3: Horizontal Scaling (10x Load)

```
┌──────────────────┐
│  Load Balancer   │
└────────┬─────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│Backend│ │Backend│ │Backend│ │Backend│
│ 1-25  │ │26-50  │ │51-75  │ │76-100│
│strat. │ │strat. │ │strat. │ │strat. │
└───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
    │        │        │        │
    └────┬───┴────┬───┴────┬───┘
         │        │        │
    ┌────▼────────▼────────▼────┐
    │  Shared Data Layer         │
    │  • PostgreSQL Cluster      │
    │  • Redis Cluster           │
    │  • Kafka (Event Stream)    │
    └────────────────────────────┘

Capacity: 100k ticks/sec, 10k orders/min
```

---

**END OF DIAGRAMS**

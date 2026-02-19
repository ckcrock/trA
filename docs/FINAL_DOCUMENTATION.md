# Final Documentation: Hybrid Trading Platform (`trA`)

Date: February 19, 2026  
Status: Current implemented baseline  
Audience: Developers, operators, and reviewers

## 1. Purpose

This document is the final consolidated reference for the current codebase state.  
It replaces fragmented operational notes by giving one accurate runbook for:

1. Architecture and component boundaries
2. Setup and runtime commands
3. API and WebSocket interfaces
4. UI and observability dashboards
5. Testing, troubleshooting, and known limitations

## 2. System Overview

The platform combines:

1. Angel One adapters (auth, market data, execution, websocket)
2. Nautilus-based trading runtime integration
3. FastAPI control plane
4. Data bridge for threaded websocket -> async broadcast flow
5. Browser UI terminal
6. Prometheus + Grafana observability stack

Core control flow:

1. Broker websocket ticks enter `src/adapters/angel/websocket_client.py`
2. Ticks are normalized/queued in `src/bridge/data_bridge.py`
3. `src/bridge/websocket_broadcaster.py` pushes ticks to UI websocket clients
4. API routes in `src/api/routes/*` provide control and query endpoints
5. Metrics are exposed at `/metrics` and visualized in Grafana

## 3. Repository Map (Current)

Primary runtime paths:

1. `src/api/main.py`
2. `src/api/routes/orders.py`
3. `src/api/routes/market_data.py`
4. `src/api/routes/instruments.py`
5. `src/api/routes/positions.py`
6. `src/api/routes/strategies.py`
7. `src/api/routes/websocket.py`
8. `src/bridge/data_bridge.py`
9. `src/adapters/angel/*`
10. `src/adapters/nautilus/*`

UI:

1. `src/ui/index.html`
2. `src/ui/static/css/style.css`
3. `src/ui/static/js/app.js`
4. `src/ui/static/js/websocket.js`

Monitoring:

1. `monitoring/prometheus.yml`
2. `monitoring/grafana/provisioning/datasources/datasource.yml`
3. `monitoring/grafana/provisioning/dashboards/dashboard.yml`
4. `monitoring/grafana/dashboards/trading-platform-overview.json`
5. `monitoring/grafana/dashboards/trading-execution-quality.json`
6. `monitoring/grafana/dashboards/trading-risk-portfolio.json`
7. `monitoring/grafana/dashboards/trading-market-data-integrity.json`

## 4. Prerequisites

1. Python 3.10+ (virtual environment recommended)
2. Docker Desktop (for Prometheus/Grafana containers)
3. Angel One credentials
4. Windows PowerShell (commands below are written for Windows)

## 5. Environment Variables

Required:

1. `ANGEL_API_KEY`
2. `ANGEL_CLIENT_CODE`
3. `ANGEL_PASSWORD`
4. `ANGEL_TOTP_SECRET`

Optional but recommended:

1. `ANGEL_HIST_API_KEY`
2. `ENABLE_BROKER_WS` (`true`/`false`)
3. `BROKER_DEFAULT_SUBSCRIPTIONS` (JSON token-group array)
4. `BROKER_WS_MODE` (default `1`)
5. `CORS_ALLOW_ORIGINS` (comma-separated)
6. `CORS_ALLOW_CREDENTIALS` (`true`/`false`)

Order-guard controls:

1. `ENFORCE_ORDER_GUARDS`
2. `ALLOW_OFF_MARKET_ORDERS`
3. `MARKET_ORDER_REFERENCE_PRICE`
4. `PAPER_CAPITAL`

## 6. Setup

```powershell
python -m venv venv
venv\Scripts\activate
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
```

## 7. Runbook

### 7.1 Start API

```powershell
venv\Scripts\python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Endpoints:

1. API docs: `http://localhost:8000/api/docs`
2. Health: `http://localhost:8000/health`
3. Metrics: `http://localhost:8000/metrics`

### 7.2 Start Monitoring

```powershell
docker compose up -d prometheus grafana
```

Access:

1. Prometheus: `http://localhost:9090`
2. Grafana: `http://localhost:3000` (default `admin/admin` unless changed)

### 7.3 UI

UI files are under `src/ui/` and expect API/WebSocket on the same origin host.  
Production deployment should serve UI and API behind the same host/port via reverse proxy or application static mounting.

## 8. API Reference (Current)

Base health and stream:

1. `GET /health`
2. `WS /ws/stream`

Orders:

1. `POST /api/orders/`
2. `GET /api/orders/book`
3. `GET /api/orders/{order_id}`
4. `DELETE /api/orders/{order_id}`
5. `GET /api/orders/trades/book`

Positions:

1. `GET /api/positions/`

Instruments:

1. `GET /api/instruments/resolve?symbol=SBIN-EQ&exchange=NSE`

Market data:

1. `GET /api/market/ltp`
2. `GET /api/market/quote`
3. `GET /api/market/history`

Strategies:

1. `GET /api/strategies/`
2. `GET /api/strategies/{name}`
3. `POST /api/strategies/{name}/start`
4. `POST /api/strategies/{name}/stop`
5. `POST /api/strategies/{name}/pause`
6. `POST /api/strategies/{name}/resume`

## 9. WebSocket Contract (`/ws/stream`)

Client -> server subscribe:

```json
{"action":"subscribe","channel":"market_data"}
```

Client -> server keepalive:

```json
{"action":"ping"}
```

Server -> client tick:

```json
{
  "type": "TICK",
  "data": {
    "symbol": "SBIN-EQ",
    "token": "3045",
    "timestamp": "2026-02-19T12:00:00+00:00",
    "ltp": 725.5
  }
}
```

## 10. Observability and Dashboards

Metrics are exposed through Prometheus format at `/metrics`.

Provisioned Grafana dashboards:

1. Trading Platform Overview
2. Trading Execution Quality
3. Trading Risk And Portfolio
4. Trading Market Data Integrity

Primary tracked areas:

1. Order placement/rejection/latency
2. WebSocket connectivity/reconnects/subscription errors
3. Tick throughput, invalid/dropped ticks, bridge queue depth
4. API request rate and latency
5. Portfolio and strategy activity gauges

## 11. Testing and Validation

Full test command (validated):

```powershell
set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
set PYTHONPATH=.
pytest -q -p no:cacheprovider -p pytest_asyncio
```

Python syntax check example:

```powershell
python -m py_compile src/api/main.py src/api/routes/orders.py src/api/routes/websocket.py src/bridge/data_bridge.py src/adapters/angel/websocket_client.py
```

Basic runtime smoke checks:

1. `GET /health` returns HTTP `200`
2. `GET /metrics` returns Prometheus metrics payload
3. Grafana health: `http://localhost:3000/api/health`
4. Prometheus health: `http://localhost:9090/-/healthy`

## 12. Troubleshooting

### 12.1 Docker daemon error on Windows

Symptom:

`open //./pipe/docker_engine: The system cannot find the file specified`

Resolution:

1. Start Docker Desktop
2. Wait until engine is running
3. Retry: `docker compose up -d prometheus grafana`

### 12.2 Grafana login fails with `401`

1. Password may have been changed from default
2. Confirm `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.yml`
3. Recreate container if needed:

```powershell
docker compose up -d --force-recreate grafana
```

### 12.3 Market orders rejected by risk guard

If `ENFORCE_ORDER_GUARDS=true`, market orders need a positive reference price.  
Set `MARKET_ORDER_REFERENCE_PRICE` or provide price in request payload logic.

### 12.4 No live ticks in UI

1. Ensure `ENABLE_BROKER_WS=true`
2. Validate broker auth credentials
3. Provide valid `BROKER_DEFAULT_SUBSCRIPTIONS`
4. Confirm websocket endpoint reachable at `/ws/stream`

## 13. Safety Notes

1. Keep execution disabled unless risk limits and audit checks are confirmed
2. Do not store secrets in source files
3. Validate behavior in paper-safe mode before enabling any live order flows

## 14. Known Limitations (Current)

1. UI requires same-origin serving with API; static file opening is not a complete deployment mode
2. Some historical docs still contain planned-module references not yet implemented
3. `scripts/live_nautilus.py` remains an advanced/experimental path and may require further Nautilus type-contract hardening for all live scenarios

## 15. Recommended Next Steps

1. Add static UI serving through FastAPI or reverse proxy for single-command local startup
2. Provision Grafana alert rules (reject ratio, WS reconnect spikes, tick-loss ratio)
3. Add CI docs contract validation gate for stale API references
4. Add structured run artifact logging for smoke tests


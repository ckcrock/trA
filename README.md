# trA

Algorithmic trading research and paper/live-safe runtime built with Nautilus Trader, Angel One adapters, and FastAPI control APIs.

## Overview

This repository provides:

1. Nautilus-based strategy runtime (`TradingNode`, data/execution/risk engines).
2. Angel One adapter layer for:
   - Live WebSocket market data
   - Historical candle data
   - Execution client integration (gated/safe by default in live script)
3. FastAPI routes and background services for orchestration and observability.
4. Documentation, architecture diagrams, and test suites for migration and validation.

## Key Paths

1. Core runtime:
   - `src/adapters/nautilus/data.py`
   - `src/adapters/nautilus/execution.py`
   - `src/adapters/nautilus/factories.py`
   - `src/adapters/nautilus/providers.py`
2. Angel adapters:
   - `src/adapters/angel/auth.py`
   - `src/adapters/angel/websocket_client.py`
   - `src/adapters/angel/data_client.py`
   - `src/adapters/angel/execution_client.py`
3. API/control plane:
   - `src/api/main.py`
   - `src/api/routes/orders.py`
   - `src/api/services/background_tasks.py`
4. Live run script:
   - `scripts/live_nautilus.py`
5. Tests:
   - `tests/`

## Environment Setup

```powershell
python -m venv venv
venv\Scripts\activate
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\python -m pip install -r requirements.txt
```

## Required Environment Variables

Set these in `.env` (or shell env):

1. `ANGEL_API_KEY`
2. `ANGEL_CLIENT_CODE`
3. `ANGEL_PASSWORD`
4. `ANGEL_TOTP_SECRET`
5. `ANGEL_HIST_API_KEY` (optional depending on setup)

## Run

Live-safe strategy run (no execution client wiring by default):

```powershell
venv\Scripts\python scripts/live_nautilus.py --duration 120 --instrument SBIN-EQ --exchange NSE
```

## Test

Targeted regression command:

```powershell
venv\Scripts\python -m pytest -q tests/test_nautilus_parsing.py tests/test_operational_readiness.py tests/test_api_integration.py tests/test_angel_response_normalization.py -p no:cacheprovider
```

## Architecture and Diagrams

1. Main architecture and data-flow doc:
   - `docs/SYSTEM_DIAGRAMS_AND_DATA_FLOW.md`
2. Use cases and runtime behavior:
   - `docs/USE_CASES_AND_RUNTIME_BEHAVIOR.md`
3. Draw.io + exported diagram assets:
   - `docs/diagrams/system_architecture.drawio`
   - `docs/diagrams/01_system_context.svg`
   - `docs/diagrams/02_runtime_component_architecture.svg`
   - `docs/diagrams/03_live_market_data_flow.svg`
   - `docs/diagrams/04_historical_data_flow.svg`
   - `docs/diagrams/05_execution_risk_gatekeeping.svg`
   - `docs/diagrams/06_api_bridge_control_plane.svg`
   - `docs/diagrams/07_deployment_view.svg`
   - `docs/diagrams/01_system_context.png`
   - `docs/diagrams/02_runtime_component_architecture.png`
   - `docs/diagrams/03_live_market_data_flow.png`
   - `docs/diagrams/04_historical_data_flow.png`
   - `docs/diagrams/05_execution_risk_gatekeeping.png`
   - `docs/diagrams/06_api_bridge_control_plane.png`
   - `docs/diagrams/07_deployment_view.png`

## Diagram Regeneration

```powershell
venv\Scripts\python scripts/generate_diagram_assets.py
powershell -ExecutionPolicy Bypass -File scripts/generate_diagram_pngs.ps1
```

## Current Runtime Note

On shutdown, Nautilus may log queue-cancel warnings and a trailing empty `TradingNode` error line. In current validated runs this appears as a shutdown logging artifact, not an adapter data-path failure.

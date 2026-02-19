# Use Case Documentation and Runtime Behavior Analysis

Date: 2026-02-19  
Context: Nautilus + Angel One paper/live-safe integration.

## 1. Primary Use Cases

### UC-01: Live Data Strategy Dry-Run (SAFE MODE)
- Goal: Validate full live data path, strategy lifecycle, and subscriptions without placing broker orders.
- Actors: Operator, Nautilus TradingNode, AngelOneDataClient, EMACross strategy.
- Preconditions:
  - Valid Angel credentials in environment.
  - Instrument resolves in symbol catalog (`SBIN-EQ.NSE` style).
  - WebSocket + historical auth reachable.
- Main Flow:
  1. Operator starts `scripts/live_nautilus.py`.
  2. Node builds data client via `AngelOneDataClientFactory`.
  3. Auth manager logs in and connects websocket.
  4. Strategy starts and issues `SubscribeBars`.
  5. Data client subscribes token stream and aggregates/publishes bars.
  6. Operator stops process gracefully.
- Success Criteria:
  - Node reaches `RUNNING`.
  - `Subscribed bars for ...` appears.
  - No adapter contract/type exceptions.

### UC-02: Historical Data Pull for Strategy Input
- Goal: Retrieve and normalize historical candles for strategy/backtest hydration.
- Actors: Strategy/DataEngine, AngelOneDataClient, Angel REST historical endpoint.
- Preconditions:
  - Valid token/exchange mapping.
  - Requested interval supported.
- Main Flow:
  1. Engine issues `RequestBars`.
  2. Data client calls Angel historical API.
  3. Rows parse to Nautilus `Bar`.
  4. Bars are published back to DataEngine.
- Success Criteria:
  - Bars published count > 0 in normal market history window.

### UC-03: API Control Plane + Streaming
- Goal: Operate strategies and observe live state via FastAPI and websocket broadcast.
- Actors: UI/API client, FastAPI routes, background services, bridge broadcaster.
- Main Flow:
  1. Client hits REST endpoints (orders/strategies/health).
  2. Services call bridge and runtime services.
  3. Events broadcast to websocket clients.
- Success Criteria:
  - API healthy.
  - Clients receive live updates without blocking strategy loop.

### UC-04: Execution Enablement (Future Controlled Rollout)
- Goal: Enable real execution only after data-path hardening.
- Actors: Strategy, RiskEngine, ExecEngine, Angel execution adapter.
- Guardrails:
  - Explicit execution enable flag.
  - Position/order/risk thresholds.
  - Audit logs for intent -> decision -> broker response.

## 2. Runtime Sequence Interpretation (Your Log)

Window analyzed: `2026-02-19 16:27:48` to `2026-02-19 16:27:58`.

### 2.1 What is healthy in the log

1. Startup reconciliation and auth are normal:
   - `Awaiting startup reconciliation...`
   - `Re-authenticating...`
   - `Logging in to Angel One...`
   - `Historical API client authenticated`
   - `Successfully logged in`
2. Connection path is normal:
   - `DataClient-ANGELONE-DATA: Connected`
   - `Execution state reconciled`
   - `Portfolio initialized`
3. Strategy lifecycle is normal:
   - `EMACross ... SubscribeBars(...)`
   - `EMACross ... RUNNING`
   - `TradingNode: RUNNING`
4. Subscription handshake is normal:
   - `Websocket connected`
   - `Subscribed to 1 token groups in mode 2`
   - `Subscribed to SBIN-EQ.NSE token=3045 exchange=NSE`
   - `Subscribed bars for SBIN-EQ.NSE-1-MINUTE-MID-EXTERNAL`

Conclusion: end-to-end startup and data subscription succeeded.

### 2.2 Why shutdown warnings appear

At stop:
- `DataCommand/DataResponse/Data message queue canceled`
- `RiskEngine ... run_cmd_queue canceled`
- `ExecEngine ... run_cmd_queue/run_evt_queue canceled`

This is expected during graceful node shutdown in Nautilus async runtime. It indicates loop task cancellation, not a strategy/data-path failure.

### 2.3 About final blank error line

The line:
- `TradingNode: [ERROR]` (empty message)

is a known shutdown artifact from cancellation handling/log formatting path in Nautilus runtime callbacks, not a broker/auth/subscription failure in this run.

Practical interpretation:
- Treat this as low-severity logging artifact unless accompanied by traceback/exception payload.

## 3. Operational Runbook Notes

### Recommended live-safe validation command

```powershell
venv\Scripts\python scripts/live_nautilus.py --duration 120 --instrument SBIN-EQ --exchange NSE
```

### What to verify each run

1. `TradingNode: RUNNING`
2. `DataClient-ANGELONE-DATA: Connected`
3. `SubscribeBars(...)` emitted by strategy
4. `Subscribed bars for ...` emitted by data client
5. No adapter `TypeError/ValueError` traces

## 4. Remaining Validation Gap

- Confirm at least one fully closed 1-minute bar emission during active market ticks (run >=70 seconds during market activity).
- Add explicit test/assertion around bar emission counter.

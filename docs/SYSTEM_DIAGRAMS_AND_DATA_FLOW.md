# System Diagrams, Architecture, and Data Flow

Date: 2026-02-19  
Scope: Current Nautilus + Angel One integration in this repository (paper/live-safe mode).

## 1. System Context

```mermaid
flowchart LR
    U[User / Operator] --> API[FastAPI Layer]
    U --> LIVE[scripts/live_nautilus.py]

    LIVE --> NODE[Nautilus TradingNode]
    API --> BRIDGE[Bridge + Background Tasks]

    NODE --> DCLIENT[AngelOneDataClient]
    NODE --> ECLIENT[AngelOneExecutionClient]
    NODE --> STRAT[Strategies]

    DCLIENT --> WS[Angel WebSocket]
    DCLIENT --> HIST[Angel Historical REST]
    ECLIENT --> ORD[Angel Order REST]

    WS --> EXCH[(Market Data)]
    HIST --> EXCH
    ORD --> EXCH
```

## 2. Runtime Component Architecture

```mermaid
flowchart TB
    subgraph NautilusRuntime[Nautilus Runtime]
      TN[TradingNode]
      DE[DataEngine]
      EE[ExecEngine]
      RE[RiskEngine]
      ST[EMACross / Strategy]
      TN --> DE
      TN --> EE
      TN --> RE
      TN --> ST
    end

    subgraph Adapter[Angel Adapter Layer]
      F[Data/Exec Factories]
      P[AngelOneInstrumentProvider]
      DC[src/adapters/nautilus/data.py]
      XC[src/adapters/nautilus/execution.py]
      NORM[src/adapters/nautilus/parsing.py]
      F --> DC
      F --> XC
      DC --> P
      DC --> NORM
    end

    subgraph Broker[Angel One]
      AUTH[src/adapters/angel/auth.py]
      WS2[src/adapters/angel/websocket_client.py]
      RESTD[src/adapters/angel/data_client.py]
      RESTX[src/adapters/angel/execution_client.py]
      AUTH --> WS2
      AUTH --> RESTD
      AUTH --> RESTX
    end

    TN --> F
    DC --> WS2
    DC --> RESTD
    XC --> RESTX
```

## 3. Live Market Data Flow (Tick -> Strategy)

```mermaid
sequenceDiagram
    participant WS as Angel WS
    participant ADC as AngelOneDataClient
    participant PR as Parsing/Provider
    participant DE as Nautilus DataEngine
    participant ST as Strategy

    WS->>ADC: tick payload
    ADC->>PR: parse_quote_tick + token->instrument resolve
    PR-->>ADC: QuoteTick
    ADC->>DE: _handle_data(QuoteTick)
    DE->>ST: on_quote_tick / subscriptions

    Note over ADC: For bar subscriptions
    ADC->>ADC: _update_live_bar_subscriptions()
    ADC->>ADC: aggregate tick bucket (1m, 5m, ...)
    ADC->>DE: _handle_data(Bar) on bucket close
    DE->>ST: on_bar()
```

Key implementation points:
- Subscription entry: `src/adapters/nautilus/data.py:_subscribe_bars`.
- Token routing map: provider-managed (`instrument_id -> token`) in `src/adapters/nautilus/providers.py`.
- Tick normalization and timestamp handling in `src/adapters/nautilus/parsing.py` and `src/adapters/nautilus/data.py`.

## 4. Historical Data Flow

```mermaid
sequenceDiagram
    participant ST as Strategy / Engine
    participant DE as DataEngine
    participant ADC as AngelOneDataClient
    participant REST as Angel Historical REST

    ST->>DE: RequestBars
    DE->>ADC: _request_bars(request)
    ADC->>REST: get_historical_data(token, exchange, interval, from, to)
    REST-->>ADC: candles dataframe
    ADC->>ADC: parse_bar per row
    ADC->>DE: _handle_data(Bar)*N
    DE->>ST: bar callbacks
```

## 5. Execution and Risk Gatekeeping Flow

```mermaid
flowchart LR
    SIG[Strategy Signal] --> ORD[Order Intent]
    ORD --> REQ[Risk Checks]
    REQ -->|pass| EXE[ExecEngine]
    REQ -->|reject| EVT[Reject Event + Logs]
    EXE --> ADP[Angel Execution Adapter]
    ADP --> BRK[Broker REST]
    BRK --> ACK[Ack/Fill/Reject]
    ACK --> EXE
    EXE --> POS[Positions / PnL / State]
```

Current status:
- Live script currently runs SAFE MODE without execution client wiring by default.
- This keeps data/strategy runtime verifiable without broker-side order placement.

## 6. API + Bridge Flow (control plane)

```mermaid
flowchart TB
    UI[Client/UI] --> REST[FastAPI Routes]
    REST --> SVC[Services + Background Tasks]
    SVC --> BR[Bridge/Data Broadcast]
    BR --> WSAPI[API WebSocket Broadcaster]
    WSAPI --> UI
```

Primary relevant files:
- `src/api/main.py`
- `src/api/routes/orders.py`
- `src/api/services/background_tasks.py`
- `src/bridge/data_bridge.py`

## 7. Deployment View (single-host baseline)

```mermaid
flowchart TB
    subgraph Host[Windows/Linux Host]
      API[FastAPI Process]
      NODE[Nautilus TradingNode Process]
      SCHED[Background Tasks]
      CAT[(Instrument Catalog CSV Cache)]
      LOG[(Logs/Metrics)]
    end

    API <-->|local calls/events| NODE
    NODE --> CAT
    API --> CAT
    NODE --> LOG
    API --> LOG
```

## 8. Reliability and Failure Handling

- WS disconnect:
  - reconnect path via Angel auth + websocket client.
  - subscription map must be replayed after reconnect.
- Broker/auth expiry:
  - auth manager re-auth flow refreshes session.
- Graceful shutdown:
  - node stop triggers queue cancellations (expected warnings in Nautilus logs).
- Data integrity:
  - provider token mapping avoids mutable instrument attribute assumptions.
  - normalization layer handles timestamp and paise/price conversion edge cases.

## 9. Performance and Optimization Focus

- Hot path:
  - WS tick parse -> quote publish -> optional bar aggregation.
- Keep allocations minimal in `_process_tick` and bar update loop.
- Avoid repeated symbol resolution lookups by caching token->instrument mapping.
- Add metrics counters:
  - ticks received/sec
  - bars emitted/sec
  - WS reconnect count
  - parse failures

## 10. Security and Operational Controls

- Secrets only via environment variables (`ANGEL_API_KEY`, `ANGEL_CLIENT_CODE`, etc.).
- No credentials in code/docs.
- Keep execution disabled unless explicit `--enable-execution` control and risk caps are active.
- Audit logs for order intents and risk decisions before enabling live execution.

## 11. Gaps and Next Implementation Steps

1. Add explicit unsubscribe handlers in `src/adapters/nautilus/data.py`.
2. Add live-bar emission test with mocked tick stream.
3. Add startup/shutdown health summary in `scripts/live_nautilus.py`.
4. Add structured metrics export for adapter and strategy loops.
5. Verify 70+ second market run to confirm emitted 1-minute bars in active market conditions.

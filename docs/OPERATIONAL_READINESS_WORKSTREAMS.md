# Operational Readiness: Detailed Workstreams and File-Level Tasks

Generated on: 2026-02-19

## Scope

This plan focuses on:
- Data Pipeline and WebSocket
- Historical Data Reliability
- Execution and Risk Gatekeeping

## Workstream 1: Data Pipeline and WebSocket

### Goal
Ensure malformed ticks do not poison downstream state and that latency/backpressure are measurable.

### Implemented
- Tick payload contract validation in bridge ingest path.
- Invalid tick drop accounting.
- Throughput/latency benchmark harness.

### File-level tasks
1. `src/bridge/data_bridge.py`
- Keep minimal contract in `_is_valid_tick()`.
- Preserve `seq` for latency correlation in benchmarks.
- Add bounded subscriber execution timeout (next step).

2. `src/adapters/angel/websocket_client.py`
- Add parsing for known tick schemas (ltp/quote/depth modes).
- Add stale-connection watchdog and auto-resubscribe audit logging.

3. `src/observability/metrics.py`
- Keep counters for receive/drop/invalid tick classes.
- Add queue utilization histogram (next step).

4. `scripts/benchmark_data_bridge.py`
- Add workload profiles: burst, sustained, multi-subscriber fanout.

## Workstream 2: Historical Data Reliability

### Goal
Avoid silent data corruption by enforcing column/schema continuity and gap visibility.

### Implemented
- Basic historical dataframe schema validation.
- Continuity summary (`gap_count`, `duplicate_count`) on chunked merges.

### File-level tasks
1. `src/adapters/angel/data_client.py`
- Enforce strict schema (`timestamp/open/high/low/close/volume`).
- Continue chunked fetch with dedupe + sort.
- Emit continuity warnings for large temporal gaps.

2. `src/data/data_manager.py`
- Add optional gap-fill/repair mode for backtests.
- Persist continuity report sidecar JSON per cached dataset (next step).

3. `tests/test_backtesting.py`
- Add deterministic tests for gap detection and continuity metadata persistence.

## Workstream 3: Execution and Risk Gatekeeping

### Goal
Block invalid orders at source and maintain deterministic rejection behavior.

### Implemented
- Pre-submit validation in execution client:
  - symbol token format
  - exchange, side, type, product, variety enums
  - quantity/price/trigger constraints

### File-level tasks
1. `src/adapters/angel/execution_client.py`
- Keep preflight guard as first step before auth/rate-limit spend.
- Add typed rejection reasons map (next step).

2. `src/api/routes/orders.py`
- Align adapter preflight failures with route-level structured errors.
- Add explicit circuit-breaker gate (market-wide + symbol-level) before place.

3. `src/risk/position_sizer.py`
- Add margin-aware checks by product/exchange slab and lot constraints.

4. `tests/test_api_integration.py`
- Add API-level assertions for deterministic rejection payloads.

## Operational Gate Checklist

1. Data pipeline
- Invalid ticks are dropped and counted.
- Queue drops remain under threshold in benchmark runs.

2. Historical reliability
- Missing/invalid schema rejected early.
- Gap/duplicate summary visible in logs and reports.

3. Execution/risk
- Invalid orders fail before broker call.
- Rejections remain structured and stable.

## Immediate Next Execution Batch

1. Add subscriber timeout/isolated failure handling in bridge fanout.
2. Add route-level mapping for adapter preflight validation failures.
3. Add CI command group:
- `venv\Scripts\python -m pytest -q tests\test_operational_readiness.py`
- `venv\Scripts\python -m pytest -q tests\test_angel_response_normalization.py tests\test_api_integration.py`
- `venv\Scripts\python scripts\benchmark_data_bridge.py --ticks 10000 --subscribers 2`


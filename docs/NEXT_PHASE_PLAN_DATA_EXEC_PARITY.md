# Next Phase Plan: Data + Execution Quality, Performance + Parity

Generated on: 2026-02-19

## Objective

Raise broker adapter reliability to production-like paper-trading quality with measurable parity and performance gates.

## Track A: Data + Execution Quality

### A1. Response Contract Normalization

- Implemented shared normalizer: `src/adapters/angel/response_normalizer.py`
- Wired into:
  - `src/adapters/angel/data_client.py`
  - `src/adapters/angel/execution_client.py`

### A2. Parity Contract (Paper vs Broker-Mocked)

Expected parity dimensions:

1. Order placement outcomes
- Accept both SmartAPI variants: raw string order id and dict payload.
- Normalize rejection flow to deterministic error shape.

2. Market data snapshots
- LTP/Quote parsing must survive payloads with/without explicit `status`.
- Historical candle fetch must use consistent retry/error parsing.

3. State semantics
- `placed`, `cancelled`, `not found`, `broker failure` must map to stable API behavior.

### A3. Quality Test Gates

Current coverage added:

- `tests/test_angel_response_normalization.py`
  - response normalization shape checks
  - order-id extraction variants
  - execution placement variant handling
  - ltp/quote normalized parsing

Baseline pass criteria:

- `venv\Scripts\python -m pytest -q tests\test_angel_response_normalization.py`
- `venv\Scripts\python -m pytest -q tests\test_api_integration.py`

## Track B: Performance + Parity

### B1. DataBridge Throughput Harness

- Added benchmark script: `scripts/benchmark_data_bridge.py`
- Added sequence passthrough for latency measurement: `src/bridge/data_bridge.py` (`seq` field)

Run:

```powershell
venv\Scripts\python scripts\benchmark_data_bridge.py --ticks 20000 --subscribers 2
```

Outputs:

- ticks sent
- callback-processed count
- throughput (ticks/sec)
- dropped ticks
- latency p50/p95

### B2. Next Verification Steps

1. Set explicit acceptance thresholds (example):
- drop rate <= 0.1%
- p95 latency <= 10ms (single-node local benchmark target)
- no API contract regressions in integration tests

2. Add CI step:
- run normalization tests on every push
- run benchmark in nightly mode and track baseline drift

3. Extend parity tests:
- cancel/modify/order-book variants
- quote schema field presence checks
- historical chunk stitching consistency (duplicate and ordering guarantees)


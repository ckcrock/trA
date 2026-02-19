# TODO: Nautilus Live Migration (Angel One)

Date: 2026-02-19  
Owner: Trading Platform Team  
Goal: Make `scripts/live_nautilus.py` run clean end-to-end using real adapter factories.

## 1. Scope

This TODO tracks migration from legacy manual websocket/bar wiring to proper Nautilus adapter wiring:

1. Use `AngelOneDataClientFactory` and `AngelOneDataClientConfig`.
2. Route data through Nautilus `LiveMarketDataClient` contract.
3. Support strategy bar subscriptions (`SubscribeBars`) in adapter data client.
4. Keep execution in SAFE MODE until explicit go-live gating is complete.

## 2. Status Board

## Completed

- [x] Replaced legacy manual client path in `scripts/live_nautilus.py`.
- [x] Switched to real factory registration (`ANGELONE` + `AngelOneDataClientFactory`).
- [x] Added symbol catalog preflight resolution before starting node.
- [x] Fixed instrument precision mismatch by deriving `price_precision` from `price_increment`.
- [x] Fixed Nautilus factory compatibility (`create` classmethod signature).
- [x] Fixed Nautilus config compatibility (removed `pydantic.Field` usage from live config structs).
- [x] Fixed provider compatibility for Nautilus `1.222.0` import surface and `InstrumentProvider` contract.
- [x] Fixed async method contract in `AngelOneDataClient` (`_connect`, subscriptions, requests).
- [x] Fixed broker token mapping for immutable Nautilus instruments via provider token registry.
- [x] Added live bar subscription support in `src/adapters/nautilus/data.py`:
  - [x] Implemented `_subscribe_bars(...)`.
  - [x] Added live tick-to-bar aggregation.
  - [x] Added bar flush on disconnect.
- [x] Preserved SAFE MODE (no execution client configured by script).
- [x] Verified live smoke run:
  - [x] node build/start succeeds
  - [x] WS connects
  - [x] strategy sends `SubscribeBars`
  - [x] adapter subscribes token and bar stream
  - [x] node stops cleanly with expected queue-cancel warnings

## In Progress

- [ ] Confirm bar emission over >= 70 seconds during active market ticks (1-minute aggregation).

## Pending

- [ ] Add explicit adapter integration test for bar subscription lifecycle (`SubscribeBars` -> Bar emission).
- [ ] Add structured runtime metrics in script:
  - [ ] quote ticks received
  - [ ] bars emitted
  - [ ] bar subscription state
- [ ] Add `--exchange` variants test matrix (`NSE`, `NFO`, `BSE`) with token resolution checks.
- [ ] Decide whether to keep script-level instrument injection or migrate to full instrument provider loading flow.
- [ ] Add execution client wiring behind `--enable-execution` flag with hard risk guardrails.

## 3. File-Level Work Items

1. `scripts/live_nautilus.py`
- [x] Factory-driven data client wiring
- [x] Strategy startup with configurable instrument/bar setup
- [ ] Add deterministic pass/fail summary print at shutdown

2. `src/adapters/nautilus/data.py`
- [x] Quote subscription wiring
- [x] Bar subscription handling
- [x] Live bar aggregation loop
- [ ] Add unsubscription handlers for bars/quotes (cleanup completeness)

3. `tests/`
- [ ] Add new adapter live-bar unit tests (mocked tick stream)
- [ ] Add short integration smoke for factory wiring in node startup

## 4. Acceptance Criteria

Migration is considered complete when all are true:

1. `scripts/live_nautilus.py` starts node, subscribes bars, and stops without adapter type/contract exceptions.
2. At least one bar is emitted during a live market run window.
3. Strategy subscribes to configured `bar_type` without routing errors.
4. Test coverage exists for bar subscription and aggregation basics.

## 6. Known Runtime Notes

- Nautilus emits queue-cancel warnings at shutdown in this run mode; these are expected on graceful stop.
- A trailing empty `TradingNode` error line is observed from Nautilus cancellation logging path, not from adapter exceptions.

## 5. Run Commands

Primary run:

```powershell
venv\Scripts\python scripts/live_nautilus.py --duration 120 --instrument SBIN-EQ --exchange NSE
```

Regression checks:

```powershell
venv\Scripts\python -m pytest -q tests/test_nautilus_parsing.py tests/test_operational_readiness.py tests/test_api_integration.py tests/test_angel_response_normalization.py -p no:cacheprovider
```

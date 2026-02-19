# Nautilus Trader Root Cause Report

Generated on: 2026-02-19
Target version: Nautilus Trader `1.222.0`

## Executive Summary

The primary integration failures were caused by **API contract drift** between older adapter patterns and the current Nautilus `1.222.0` live adapter interfaces.  
Most critical issues were not broker-side; they were local adapter-level mismatches which prevented execution/data paths from running.

## Verified Root Causes

1. Legacy import paths disabled adapter activation.
- Files used deprecated imports from `nautilus_trader.adapters.env` and `nautilus_trader.common.logging`.
- In `1.222.0`, live clients are in `nautilus_trader.live.*`, and logger type is available via `nautilus_trader.common.component`.
- Impact: `NAUTILUS_AVAILABLE` fell back to `False`, adapter classes degraded to dummy mode.

2. Factory type registration mismatch.
- `TradingNode` in this version uses `add_data_client_factory` / `add_exec_client_factory` (class types), not `register_*`.
- Impact: factories were rejected or never wired correctly to live node.

3. Client override method signatures were incompatible.
- Local adapters implemented async overrides (`async def _connect`, `async def _submit_order`, etc.).
- Nautilus expects synchronous override signatures and internal task scheduling.
- Impact: coroutines could be returned without execution in callback-driven paths.

4. Constructor argument mismatch for live clients.
- Local super calls passed unsupported parameters (for example, `logger`) and missed required order/fields (for example, `instrument_provider` for market/execution clients).
- Impact: runtime failures when Nautilus attempted to instantiate clients.

5. Execution response contract mismatch.
- Adapter assumed broker `place_order` returns dict status payload.
- Actual Angel execution client returns `order_id: str | None`.
- Impact: valid order submissions could be marked as rejected.

6. Data path had partial schema drift in quote/exchange mapping.
- WS quote translation missed normalized key variants in some bridge paths.
- Exchange segment derivation could leak internal `ANGELONE` venue value into broker subscription/history payloads.
- Impact: live tick delivery could silently degrade for some symbols/venues even when core adapter booted.

## Evidence (Local Runtime + Docs)

1. Installed version and API verification:
- `nautilus_trader.__version__ == 1.222.0`
- `TradingNode.add_data_client_factory` / `add_exec_client_factory` signatures verified at runtime.
- `LiveDataClientFactory.create` and `LiveExecClientFactory.create` signatures verified at runtime.

2. Official docs checked:
- Live adapter concepts and expected override patterns:
  - https://nautilustrader.io/docs/latest/concepts/live/
- Integration examples showing factory registration (`add_data_client_factory`, `add_exec_client_factory`):
  - https://nautilustrader.io/docs/latest/integrations/binance/

3. Upstream codebase reference:
- https://github.com/nautechsystems/nautilus_trader

## What Was Corrected

1. Updated adapter imports to current `live.*` APIs.
2. Corrected node registration flow to use `add_*_client_factory` compatibility.
3. Normalized client method contracts to synchronous overrides with async task bridging.
4. Corrected execution adapter to handle order id string return contract.
5. Hardened factory module so `NAUTILUS_AVAILABLE` remains true under current API layout.
6. Fixed tooling scripts causing false negatives (`check_config_types.py`, `check_nautilus_types_v2.py`).

## Remaining Gaps (Not Yet Fully Closed)

1. Instrument provider still uses lightweight fallback references when full Nautilus instrument construction fails for some symbols:
- `src/adapters/nautilus/providers.py`

2. End-to-end live order/data parity test with real broker session is still required.

3. Historical request window handling should still be validated against live Nautilus request payloads under full node runtime.

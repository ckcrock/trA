# Strategy Correctness and Parity: Traceability Matrix

Generated on: 2026-02-19

## Scope

This document maps strategy behavior contracts to implementation files and automated tests.

## Contracts

1. Signal schema is deterministic and traceable.
2. Signal types are validated.
3. Position accounting is correct for long/short add/reduce paths.
4. Lifecycle status reflects actual emitted strategy signals.
5. Backtest and runtime strategy interfaces remain parity-compatible.

## File-Level Mapping

1. Signal contract and position accounting
- `src/strategies/base_strategy.py`
  - `generate_signal(...)`: traceable `signal_id`, `schema_version`, typed price
  - `update_position(...)`: weighted average entry for added shorts
  - `import_state(...)`: signal sequence continuity after restore

2. Lifecycle parity visibility
- `src/engine/lifecycle.py`
  - `get_status(...)`: dynamic `signal_count` sourced from strategy instance

3. Backtest parity interface
- `src/backtesting/engine.py`
  - Uses strategy callback interface and `update_position(...)`
  - Ensures simulated fills mirror strategy position updates

## Test Mapping

1. Signal schema + validation + position accounting + lifecycle signal parity
- `tests/test_strategy_correctness_parity.py`
  - `test_signal_schema_contains_trace_fields`
  - `test_signal_type_validation`
  - `test_short_position_weighted_average_entry`
  - `test_lifecycle_signal_count_tracks_strategy_signals`

2. Existing integration anchors
- `tests/test_backtesting.py`
- `tests/test_all_modules.py`
- `tests/test_api_integration.py`

## Operational Notes

1. Any schema change in strategy signals must be versioned via `schema_version`.
2. Any lifecycle status format change must update this document and tests.
3. New strategy subclasses should inherit `BaseStrategy` signal and position contracts unchanged unless versioned.

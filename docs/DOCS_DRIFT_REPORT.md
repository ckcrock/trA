# Docs Drift Report

Generated on: 2026-02-19
Source: `venv\Scripts\python scripts\check_docs_contracts.py`

## Current Status

- Doc path refs scanned: `66`
- Missing file refs: `37`
- Doc API refs scanned: `8`
- Stale API refs: `0`

## Interpretation

- API documentation is now aligned with current FastAPI routes.
- Remaining drift is mostly roadmap-style references to planned modules/files that do not exist yet in this repository.

## Priority Actions

1. Keep architecture docs as "planned" but avoid presenting planned paths as implemented artifacts.
2. Add a "Planned (not yet implemented)" section in docs that list future files explicitly.
3. Re-run docs contract check in CI and fail only on stale API refs for now.
4. Convert selected high-priority planned modules into tracked implementation tickets.

## High-Impact Missing Paths (Sample)

- `src/backtesting/backtest_engine.py`
- `src/data/historical_data_manager.py`
- `src/paper_trading/paper_engine.py`
- `src/analytics/indian_market_metrics.py`
- `scripts/deploy.sh`
- `scripts/setup_database.py`

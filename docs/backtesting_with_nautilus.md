# Backtesting with NautilusTrader

This guide explains how to run backtests using the NautilusTrader engine in this project.

## Overview
The backtesting system uses:
- **`HistoricalDataManager`**: To fetch, sanitize, and cache historical data as Parquet files.
- **`NautilusRunner`**: To orchestrate the backtest, including engine setup, data loading, and strategy execution.
- **`scripts/run_nautilus_backtest.py`**: A ready-to-use script to executing backtests.

## Prerequisites
- Python environment with requirements installed.
- `output/` directory for logs (optional).

## 1. Data Management
NautilusTrader requires high-quality historical data. We use a local catalog of Parquet files found in `data/catalog/`.

### Fetching Real Data (Angel One)
To download real data, use the `scripts/fetch_data.py` (if implemented) or use the data manager programmatically:

```python
from src.data.data_manager import HistoricalDataManager
from src.adapters.angel.data_client import AngelDataClient

# Initialize
manager = HistoricalDataManager()
client = AngelDataClient(...)

# Download and Cache
await manager.download(
    data_client=client,
    symbol_token="3045", 
    exchange="NSE",
    interval="ONE_MINUTE",
    from_date=datetime(2023, 1, 1),
    to_date=datetime(2023, 12, 31),
    symbol_name="SBIN"
)
```

### Loading Existing Data
Data is stored as `data/catalog/{SYMBOL}_{INTERVAL}.parquet`.
The `HistoricalDataManager` automatically handles file paths.

## 2. Running a Backtest
Run the provided script to execute a backtest:

```bash
python scripts/run_nautilus_backtest.py
```

### Configuration
Edit `scripts/run_nautilus_backtest.py` to change:
- **Symbol**: `symbol = "SBIN"`
- **Strategy Config**: Adjust `fast_period`, `slow_period`, etc. in `EMACrossoverConfig`.

### Workflow
The script performs these steps:
1. **Initialize Manager**: Checks if data exists in cache.
2. **Load Data**: Loads Parquet data into Nautilus `Bar` objects.
3. **Setup Engine**: Configures a `SimulatedExchange` and `Backtester`.
4. **Run**: Executes the strategy event-by-event.
5. **Report**: Prints PnL and performance statistics.

## 3. Interpreting Results
After execution, the script prints a statistics summary:

```text
BACKTEST STATISTICS
==================================================
{'INR': {
    'PnL (total)': 150.50,         # Net Profit/Loss
    'PnL% (total)': 0.0015,        # Return %
    'Max Drawdown': -500.0,        # Maximum loss from peak
    'Sharpe Ratio': 1.2,           # Risk-adjusted return
    'Trades': 25,                  # Total trades executed
    ...
}}
```

- **PnL (total)**: The absolute profit or loss in quote currency (INR).
- **Sharpe Ratio**: A measure of risk-adjusted return (higher is better).
- **Trades**: Number of completed round-trip trades.

## 4. Developing Strategies
To create a new strategy:
1. Create a file in `src/strategies/`.
2. Inherit from `NautilusBaseStrategy` (adapter) or `Strategy` (native).
3. Implement `on_start`, `on_bar`, etc.
4. Add the strategy class in `scripts/run_nautilus_backtest.py`.

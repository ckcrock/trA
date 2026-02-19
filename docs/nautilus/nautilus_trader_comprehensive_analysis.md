# NautilusTrader Comprehensive Library Analysis

## Executive Summary

NautilusTrader is a high-performance, production-grade algorithmic trading platform with event-driven backtesting capabilities. Built with a Rust core and Python bindings, it provides identical code execution for backtesting and live trading, eliminating the traditional reimplementation gap between research and production environments.

**Version Analyzed**: 0.52.0 (Latest stable)  
**Language**: Rust core with Python/Cython bindings via PyO3  
**License**: LGPL-3.0-or-later  
**Repository**: https://github.com/nautechsystems/nautilus_trader

---

## I. CORE ARCHITECTURE

### 1.1 Main Components

#### **NautilusKernel** (Single-threaded Core)
The kernel is the central processing unit that runs on a single thread for deterministic event ordering:

- **MessageBus**: Passes messages (data, commands, events) between components
- **Actor Callback Dispatch**: Routes callbacks to registered actors
- **Strategy Logic**: Manages trading strategy execution
- **Order Management**: Handles order lifecycle
- **Risk Engine**: Validates trading commands
- **Cache**: High-performance in-memory storage
- **Portfolio**: Tracks positions and account state

#### **Multi-threaded Services** (Separate Thread Pools)
- **Persistence**: DataFusion queries and database operations via Tokio runtime
- **Adapters**: Async adapter operations via thread pool executors
- **Networking**: HTTP/WebSocket clients for venue connectivity

### 1.2 Environment Contexts

NautilusTrader supports three operational modes:

1. **Backtest**: Historical data simulation with nanosecond resolution
2. **Sandbox**: Real-time data with virtual execution (paper trading)
3. **Live**: Real-time data with actual order execution

All three contexts share the same core kernel, ensuring code parity.

---

## II. DATA STACK

### 2.1 Data Types Supported

#### Market Data Types (Descending Order of Granularity)
1. **Order Book L3** - Full depth with individual orders
2. **Order Book L2** - Market depth across all price levels
3. **Order Book L1** - Top of book (best bid/ask)
4. **Trade Ticks** - Actual executed trades
5. **Quote Ticks** - Bid/ask price updates
6. **Bar Data** - Aggregated OHLCV data (1-min, 1-hour, 1-day, etc.)
7. **Custom Data** - User-defined data types

#### Data Objects

**Built-in Data Classes:**
- `QuoteTick` - Bid/ask price and size with timestamps
- `TradeTick` - Individual trade execution data
- `Bar` - OHLCV bar with volume
- `OrderBook` - Current order book state
- `OrderBookDeltas` - Incremental order book updates
- `InstrumentStatus` - Trading status updates
- `InstrumentClose` - Session close data
- `Instrument` - Instrument definitions
- `Data` - Base class for custom data

**Precision Handling:**
- Fixed-point precision with raw values
- Price/size values must be valid multiples of scale factor
- Invalid values raise `ValueError`

### 2.2 Data Components

#### **DataEngine**
- Processes data for internal components
- Maintains historical and real-time data streams
- Publishes data events to MessageBus
- Supports multiple data feeds simultaneously

#### **DataClient** (Base Class)
Abstract base for venue-specific data clients:

**Key Methods:**
- `connect()` - Establish connection
- `disconnect()` - Close connection
- `subscribe(data_type)` - Subscribe to live data
- `unsubscribe(data_type)` - Cancel subscription
- `request(data_type)` - Request historical data

**Lifecycle States:**
- INITIALIZED → STARTING → RUNNING → STOPPING → STOPPED
- DEGRADED, FAULTED, DISPOSING, DISPOSED

#### **MarketDataClient**
Specialized data client for market data subscriptions.

#### **Data Aggregators**

**BarAggregator:**
- Aggregates tick data into bars
- Supports time-based and volume-based bars
- Maintains `historical_mode` and `is_running` flags
- Methods: `update(bar)`, `handle_quote_tick()`, `handle_trade_tick()`

### 2.3 Data Catalog

**ParquetDataCatalog:**
- Stores and retrieves data in Parquet format
- Optimized for large datasets
- Supports DataFusion queries
- Can load data exceeding available RAM (streams up to 5M rows/sec)

---

## III. EXECUTION STACK

### 3.1 Order Types

**Market Orders:**
- `MarketOrder` - Execute at best available price
- `MarketToLimitOrder` - Convert to limit after partial fill
- `MarketIfTouchedOrder` - Becomes market when price reached

**Limit Orders:**
- `LimitOrder` - Execute at specified price or better
- `LimitIfTouchedOrder` - Becomes limit when price reached
- `StopLimitOrder` - Stop with limit price

**Stop Orders:**
- `StopMarketOrder` - Stop with market execution
- `TrailingStopMarketOrder` - Trailing stop
- `TrailingStopLimitOrder` - Trailing stop with limit

**Advanced Orders:**
- Bracket orders (entry + stop loss + take profit)
- OCO (One-Cancels-Other)
- Iceberg orders
- TWAP (Time-Weighted Average Price) execution

### 3.2 Order Management

#### **OrderFactory**
Convenience factory for creating orders with reduced boilerplate:

```python
order = self.order_factory.limit(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=qty,
    price=price,
    emulation_trigger=TriggerType.LAST_PRICE  # Optional emulation
)
```

#### **Order Lifecycle Events**

**Event Sequence:**
1. `OrderInitialized` - Order created
2. `OrderDenied` - Rejected by risk engine
3. `OrderEmulated` - Sent to order emulator
4. `OrderReleased` - Released from emulation
5. `OrderSubmitted` - Sent to venue
6. `OrderAccepted` - Acknowledged by venue
7. `OrderTriggered` - Stop/limit triggered
8. `OrderFilled` - Full or partial fill
9. `OrderCanceled` - Canceled
10. `OrderExpired` - Time-based expiry
11. `OrderRejected` - Rejected by venue
12. `OrderUpdated` - Modified
13. `OrderPendingUpdate` - Modification pending
14. `OrderPendingCancel` - Cancellation pending
15. `OrderModifyRejected` - Modification rejected
16. `OrderCancelRejected` - Cancellation rejected

### 3.3 Execution Components

#### **ExecutionEngine**
Central execution coordinator:
- Routes orders to appropriate clients
- Manages order state transitions
- Coordinates with RiskEngine
- Handles reconciliation
- Supports multiple OMS types (HEDGING, NETTING)

#### **ExecutionClient** (Base Class)
Abstract base for venue-specific execution:

**Key Methods:**
- `submit_order(command)` - Submit new order
- `modify_order(command)` - Update existing order
- `cancel_order(command)` - Cancel order
- `batch_cancel_orders(commands)` - Cancel multiple orders
- `query_order(order_id)` - Check order status

**Configuration:**
- `oms_type`: HEDGING or NETTING
- `account_type`: CASH, MARGIN, or BETTING
- `base_currency`: Account base currency

#### **OrderEmulator**
Local order management for advanced order types:
- Emulates stop orders, trailing stops
- Triggers based on market data
- Releases orders to venue when triggered
- Configurable trigger types: BID, ASK, LAST, MID_POINT

**Trigger Types:**
- `DEFAULT` / `BID_ASK` - Based on bid/ask prices
- `LAST` - Based on last trade price
- `MID_POINT` - Based on mid-price
- Additional trigger types available

#### **ExecAlgorithm** (Base Class)
For implementing execution algorithms:

**Built-in Algorithms:**
- TWAP (Time-Weighted Average Price)
- VWAP (Volume-Weighted Average Price)
- Custom algorithms via subclassing

**Key Methods:**
- `spawn_market_order()` - Create child market order
- `spawn_limit_order()` - Create child limit order
- `on_start()` - Algorithm initialization
- `on_order_filled()` - Handle fill events

### 3.4 Risk Management

#### **RiskEngine**
Pre-trade risk validation:
- Maximum order size checks
- Maximum notional exposure limits
- Position limit enforcement
- Custom risk rules
- Blocks invalid commands before submission

---

## IV. POSITION & PORTFOLIO MANAGEMENT

### 4.1 Position Management

#### **Position Object**
Tracks individual positions:

**Attributes:**
- `instrument_id` - Traded instrument
- `position_id` - Unique position identifier
- `account_id` - Associated account
- `opening_order_id` - Order that opened position
- `entry` / `side` - Entry side (LONG/SHORT)
- `quantity` - Current position size
- `peak_qty` - Maximum position size reached
- `signed_qty` - Signed quantity (+ for LONG, - for SHORT)
- `ts_opened` - Opening timestamp
- `ts_closed` - Closing timestamp (if closed)
- `duration_ns` - Position duration in nanoseconds
- `avg_px_open` - Average opening price
- `avg_px_close` - Average closing price
- `realized_pnl` - Realized P&L
- `unrealized_pnl` - Unrealized P&L
- `commissions` - Total commissions paid

**Events:**
- `PositionOpened` - Position opened
- `PositionChanged` - Position modified (quantity/price)
- `PositionClosed` - Position fully closed

### 4.2 Portfolio Components

#### **Portfolio**
Central position and account tracker:

**Account Information:**
- `account(venue)` - Get account for venue
- `balances_locked(venue)` - Locked balances
- `margins_init(venue)` - Initial margin requirements
- `margins_maint(venue)` - Maintenance margin requirements
- `unrealized_pnls(venue)` - Unrealized P&L by currency
- `realized_pnls(venue)` - Realized P&L by currency
- `net_exposures(venue)` - Net exposure by currency

**Position Information:**
- `unrealized_pnl(instrument_id)` - Unrealized P&L for instrument
- `realized_pnl(instrument_id)` - Realized P&L for instrument
- `net_exposure(instrument_id)` - Net exposure for instrument
- `net_position(instrument_id)` - Net position size
- `is_net_long(instrument_id)` - Check if net long
- `is_net_short(instrument_id)` - Check if net short
- `is_flat(instrument_id)` - Check if flat
- `is_completely_flat()` - Check if no positions

#### **PortfolioAnalyzer**
Performance metrics and statistics:

**PnL Statistics:**
- Total PnL, Gross PnL, Net PnL
- Win Rate, Loss Rate
- Average Win, Average Loss
- Profit Factor
- Expectancy
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio

**Return Statistics:**
- Total Return, CAGR
- Daily/Monthly/Yearly returns
- Rolling Sharpe Ratio
- Maximum Drawdown
- Maximum Drawdown Duration

**Position Statistics:**
- Total Positions
- Win Count, Loss Count
- Long Count, Short Count
- Average Position Duration

**Order Statistics:**
- Total Orders
- Fill Rate
- Average Slippage

**Methods:**
- `add_positions(positions)` - Add position data
- `add_returns(returns)` - Add return data
- `add_trades(trades)` - Add trade data
- `calculate_statistics()` - Compute all metrics
- `get_performance_stats_pnls()` - Get P&L stats
- `get_performance_stats_returns()` - Get return stats
- `get_performance_stats_general()` - Get general stats

---

## V. CACHE SYSTEM

### 5.1 Cache Architecture

The **Cache** is an in-memory database that stores all trading-related data:

**Storage Categories:**
1. **Market Data** - Recent order books, quotes, trades, bars
2. **Execution Data** - Orders, order events, position events
3. **Position Data** - Current and historical positions
4. **Account Data** - Account states and balances
5. **Instrument Data** - Instrument definitions
6. **Custom Data** - User-defined objects

### 5.2 Cache Operations

#### **Data Retrieval**

**Market Data:**
- `quote_tick(instrument_id)` - Last quote tick
- `trade_tick(instrument_id)` - Last trade tick
- `bar(bar_type)` - Last bar
- `order_book(instrument_id)` - Current order book
- `book_update_count(instrument_id)` - Update count
- `quote_ticks(instrument_id)` - Recent quotes
- `trade_ticks(instrument_id)` - Recent trades
- `bars(bar_type)` - Recent bars

**Execution Data:**
- `order(client_order_id)` - Get order by ID
- `orders()` - All orders
- `orders_open()` - All open orders
- `orders_closed()` - All closed orders
- `orders_emulated()` - All emulated orders
- `orders_inflight()` - Orders in flight
- `orders_for_position(position_id)` - Orders for position
- `order_exists(client_order_id)` - Check if order exists

**Position Data:**
- `position(position_id)` - Get position by ID
- `positions()` - All positions
- `positions_open()` - All open positions
- `positions_closed()` - All closed positions
- `position_exists(position_id)` - Check if position exists
- `position_for_order(client_order_id)` - Position for order
- `position_snapshots(position_id)` - Position snapshots

**Instrument Data:**
- `instrument(instrument_id)` - Get instrument
- `instruments(venue)` - All instruments for venue
- `synthetics()` - All synthetic instruments

**Account Data:**
- `account(account_id)` - Get account
- `accounts()` - All accounts
- `account_for_venue(venue)` - Account for venue

#### **Cache Configuration**

**Default Limits:**
- 10,000 bars per bar type
- 10,000 trade ticks per instrument
- Configurable via `CacheConfig`

**Memory Management:**
- Automatic cleanup of old data
- Purge methods for manual cleanup
- Database persistence optional (Redis/PostgreSQL)

**Purge Methods:**
- `clear_cache()` - Clear all in-memory data
- `flush_db()` - Flush database
- `reset()` - Full reset
- `purge_order(order_id, ts_now)` - Remove specific order
- `purge_position(position_id, ts_now)` - Remove specific position

---

## VI. STRATEGY DEVELOPMENT

### 6.1 Strategy Base Class

**Strategy** inherits from **Actor**, providing:

#### **Core Capabilities (from Actor):**
- Data subscription and handling
- Time alerts and timers
- Task scheduling
- Indicator registration
- Message publishing
- Custom data handling

#### **Additional Strategy Capabilities:**
- Order management (submit, modify, cancel)
- Position tracking
- Portfolio access
- Risk management integration

### 6.2 Strategy Handlers

#### **Lifecycle Handlers**
- `on_start()` - Strategy initialization
- `on_stop()` - Strategy cleanup
- `on_resume()` - Resume from pause
- `on_reset()` - Reset state
- `on_dispose()` - Resource disposal
- `on_degrade()` - Degraded mode
- `on_fault()` - Fault handling
- `on_save()` - Save state (returns dict)
- `on_load(state)` - Load state

#### **Data Handlers**
- `on_order_book_deltas(deltas)` - Order book updates
- `on_order_book(order_book)` - Full order book
- `on_quote_tick(tick)` - Quote tick data
- `on_trade_tick(tick)` - Trade tick data
- `on_bar(bar)` - Bar data
- `on_instrument(instrument)` - Instrument updates
- `on_instrument_status(data)` - Status updates
- `on_instrument_close(data)` - Session close
- `on_historical_data(data)` - Historical data
- `on_data(data)` - Custom data
- `on_signal(signal)` - Custom signals

#### **Order Event Handlers**
- `on_order_initialized(event)` - Order created
- `on_order_denied(event)` - Risk rejection
- `on_order_emulated(event)` - Emulation started
- `on_order_released(event)` - Released from emulation
- `on_order_submitted(event)` - Submitted to venue
- `on_order_accepted(event)` - Venue accepted
- `on_order_rejected(event)` - Venue rejected
- `on_order_canceled(event)` - Order canceled
- `on_order_expired(event)` - Order expired
- `on_order_triggered(event)` - Stop/limit triggered
- `on_order_pending_update(event)` - Modify pending
- `on_order_pending_cancel(event)` - Cancel pending
- `on_order_modify_rejected(event)` - Modify rejected
- `on_order_cancel_rejected(event)` - Cancel rejected
- `on_order_updated(event)` - Order modified
- `on_order_filled(event)` - Order filled
- `on_order_event(event)` - Generic order event

#### **Position Event Handlers**
- `on_position_opened(event)` - Position opened
- `on_position_changed(event)` - Position changed
- `on_position_closed(event)` - Position closed
- `on_position_event(event)` - Generic position event

#### **Generic Handler**
- `on_event(event)` - All events eventually reach here

### 6.3 Strategy Methods

#### **Data Subscriptions**
- `subscribe_bars(bar_type, await_partial=False)` - Subscribe to bars
- `subscribe_quote_ticks(instrument_id)` - Subscribe to quotes
- `subscribe_trade_ticks(instrument_id)` - Subscribe to trades
- `subscribe_order_book_deltas(instrument_id, depth=None)` - Book deltas
- `subscribe_order_book_snapshots(instrument_id, depth=None)` - Book snapshots
- `subscribe_instrument(instrument_id)` - Instrument updates
- `subscribe_instrument_status(instrument_id)` - Status updates
- `subscribe_instrument_close(instrument_id)` - Session close
- `subscribe_data(data_type)` - Custom data subscription
- `subscribe_signals(signal_type)` - Signal subscription

**Unsubscribe methods** mirror subscribe methods.

#### **Data Requests**
- `request_bars(bar_type, start=None, end=None)` - Historical bars
- `request_quote_ticks(instrument_id, start=None, end=None)` - Historical quotes
- `request_trade_ticks(instrument_id, start=None, end=None)` - Historical trades
- `request_instrument(instrument_id)` - Instrument definition
- `request_instruments(venue)` - All instruments for venue
- `request_data(data_type)` - Custom data request

#### **Order Management**
- `submit_order(order, position_id=None)` - Submit single order
- `submit_order_list(order_list)` - Submit bracket/OCO orders
- `modify_order(order, quantity=None, price=None, trigger_price=None)` - Modify order
- `cancel_order(order)` - Cancel single order
- `cancel_orders(orders)` - Cancel batch
- `cancel_all_orders(instrument_id, side=None)` - Cancel all for instrument
- `close_position(position, client_order_id=None, tags=None)` - Close position
- `close_all_positions(instrument_id, side=None)` - Close all positions

#### **Indicator Management**
- `register_indicator_for_bars(bar_type, indicator)` - Bar updates
- `register_indicator_for_quote_ticks(instrument_id, indicator)` - Quote updates
- `register_indicator_for_trade_ticks(instrument_id, indicator)` - Trade updates

#### **Timer Management**
- `clock.set_time_alert(name, alert_time, callback=None)` - One-time alert
- `clock.set_timer(name, interval, start_time=None, stop_time=None, callback=None)` - Recurring timer
- `clock.cancel_timer(name)` - Cancel timer
- `clock.cancel_timers()` - Cancel all timers

#### **Task Management**
- `run_in_executor(func, *args)` - Run in thread pool
- `create_task(coro, log_msg=None, actions=None)` - Create async task
- `queue_for_executor(func, *args, **kwargs)` - Queue sequential task
- `cancel_task(task_id)` - Cancel specific task
- `cancel_all_tasks()` - Cancel all tasks

### 6.4 Strategy Configuration

**StrategyConfig** base class for strategy parameters:

```python
class MyStrategyConfig(StrategyConfig):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal
    order_id_tag: str  # Required for multiple instances
    
config = MyStrategyConfig(
    instrument_id="ETHUSDT-PERP.BINANCE",
    bar_type="ETHUSDT-PERP.BINANCE-15-MINUTE[LAST]-EXTERNAL",
    trade_size=Decimal("1.0"),
    order_id_tag="001"
)

strategy = MyStrategy(config)
```

**Special Features:**
- `manage_gtd_expiry=True` - Strategy manages GTD expiry
- `order_id_tag` - Required for multiple strategy instances
- Serializable for distributed systems

---

## VII. ACTORS

### 7.1 Actor Base Class

**Actor** is the base for custom components without order management:

**Use Cases:**
- Data processing
- Signal generation
- Custom analytics
- Event monitoring
- Integration with external systems

**Key Differences from Strategy:**
- No order management capabilities
- Lighter weight
- Can publish signals to strategies

### 7.2 Actor Capabilities

#### **Available Methods:**
- All data subscription methods
- All data request methods
- Indicator registration
- Timer and task management
- Cache access
- Portfolio access (read-only for positions/accounts)
- Signal publishing

#### **Not Available:**
- Order submission
- Order modification
- Order cancellation
- Position management

---

## VIII. INDICATORS

### 8.1 Built-in Indicators

#### **Moving Averages**
- `SimpleMovingAverage` (SMA) - Simple moving average
- `ExponentialMovingAverage` (EMA) - Exponential moving average
- `DoubleExponentialMovingAverage` (DEMA) - Double exponential
- `HullMovingAverage` (HMA) - Hull moving average
- `WeightedMovingAverage` (WMA) - Weighted moving average
- `AdaptiveMovingAverage` (AMA) - Kaufman's adaptive MA
- `VariableIndexDynamicAverage` (VIDYA) - Variable index dynamic
- `WilderMovingAverage` (WILMA) - Wilder's moving average
- `LinearRegression` - Linear regression line
- `VolumeWeightedAveragePrice` (VWAP) - VWAP

#### **Momentum Indicators**
- `RelativeStrengthIndex` (RSI) - RSI oscillator
- `MovingAverageConvergenceDivergence` (MACD) - MACD indicator
- `Aroon` - Aroon indicator
- `AroonOscillator` - Aroon oscillator
- `BollingerBands` - Bollinger bands
- `CommodityChannelIndex` (CCI) - CCI indicator
- `Stochastics` - Stochastic oscillator
- `RateOfChange` (ROC) - Rate of change
- `ArcherMovingAveragesTrends` (AMAT) - Archer MA trends
- `KlingerVolumeOscillator` (KVO) - Klinger oscillator
- `PsychologicalLine` - Psychological line
- `Bias` - Bias indicator

#### **Volatility Indicators**
- `AverageTrueRange` (ATR) - Average true range
- `DonchianChannel` - Donchian channels
- `KeltnerChannel` - Keltner channels
- `VolatilityRatio` - Volatility ratio
- `StandardDeviation` - Standard deviation
- `TrueRange` - True range

#### **Ratio/Spread Indicators**
- `EfficiencyRatio` - Efficiency ratio
- `SpreadAnalyzer` - Spread analysis
- `BookImbalanceRatio` - Order book imbalance

#### **Other Indicators**
- `Pressure` - Market pressure
- `SwingHigh` / `SwingLow` - Swing points
- `VerticalHorizontalFilter` (VHF) - VHF indicator
- `DirectionalMovement` (DM) - Directional movement
- `OnBalanceVolume` (OBV) - On-balance volume
- `Fuzzy` - Fuzzy candlestick patterns

### 8.2 Indicator Interface

**Common Methods:**
- `handle_bar(bar)` - Update with bar data
- `handle_quote_tick(tick)` - Update with quote
- `handle_trade_tick(tick)` - Update with trade
- `update_raw(value)` - Update with raw value
- `reset()` - Reset to initial state

**Common Properties:**
- `value` - Current indicator value
- `name` - Indicator name
- `has_inputs` - Has received data
- `initialized` - Is warmed up
- `count` - Number of inputs received

**Implementation:**
- Rust core for performance
- Python/Cython bindings
- Circular buffers for memory efficiency
- Bounded memory usage

---

## IX. BACKTESTING

### 9.1 Backtesting Architecture

**Two API Levels:**

#### **High-level API (Recommended)**
Uses `BacktestNode` with configuration:

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestEngineConfig

config = BacktestEngineConfig(
    trader_id="BACKTESTER-001",
    # ... configuration
)

node = BacktestNode(configs=[config])
node.run()
```

#### **Low-level API**
Direct `BacktestEngine` usage for advanced control:

```python
from nautilus_trader.backtest.engine import BacktestEngine

engine = BacktestEngine()
engine.add_venue(...)
engine.add_instrument(...)
engine.add_data(...)
engine.run()
```

### 9.2 BacktestEngine Components

**Key Methods:**
- `add_venue(venue, oms_type, account_type, base_currency, starting_balances)` - Add venue
- `add_instrument(instrument)` - Add instrument
- `add_data(data, sort=True)` - Add market data
- `add_actor(actor)` - Add actor component
- `add_strategy(strategy)` - Add strategy
- `add_exec_algorithm(exec_algorithm)` - Add execution algorithm
- `run(start, end, run_config_id=None)` - Execute backtest
- `reset()` - Reset engine state
- `dispose()` - Cleanup resources

**Configuration:**
- `BacktestEngineConfig` - Engine settings
- `BacktestVenueConfig` - Venue-specific settings
- `BacktestDataConfig` - Data loading settings
- `ImportableStrategyConfig` - Strategy configuration

### 9.3 Venue Simulation

**Matching Engine:**
- Order matching simulation
- Fill price calculation
- Slippage modeling
- Latency simulation
- Bar execution mode
- Order book execution mode

**Venue Features:**
- `bar_execution=True` - Execute on bar data
- `trade_execution=True` - Execute on trade data
- `liquidity_consumption=True` - Track liquidity consumption
- `reject_stop_orders=False` - Allow stop orders
- `support_gtd_orders=True` - Support GTD time in force

**Fill Models:**
- Fixed slippage
- Percentage slippage
- Dynamic spread-based

### 9.4 Data Loading

**Supported Formats:**
- Parquet files (recommended)
- CSV files
- Custom data loaders
- Streaming data

**ParquetDataCatalog:**
```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("./data")
catalog.write_data([...])  # Write data
data = catalog.load_data(...)  # Load data
```

**Performance Optimization:**
- Pre-sort data before loading
- Use `sort=False` for pre-sorted data
- Batch data loading
- Stream large datasets

---

## X. LIVE TRADING

### 10.1 TradingNode

Central component for live trading:

```python
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig

config = TradingNodeConfig(
    trader_id="TRADER-001",
    # ... configuration
)

node = TradingNode(config=config)
node.start()  # Start trading
node.stop()   # Stop trading
```

### 10.2 Live Components

#### **LiveDataClient**
Base class for live data feeds:
- Async connection management
- Automatic reconnection
- Heartbeat monitoring
- Rate limiting
- Error recovery

**Methods:**
- `connect()` - Establish connection
- `disconnect()` - Close connection
- `subscribe(data_type)` - Subscribe to data
- `unsubscribe(data_type)` - Unsubscribe
- `request(data_type)` - Request data

#### **LiveExecutionClient**
Base class for live order execution:
- Order routing to venue
- Position reconciliation
- Account state updates
- Fill reporting
- Order status monitoring

**Methods:**
- `submit_order(command)` - Submit order
- `modify_order(command)` - Modify order
- `cancel_order(command)` - Cancel order
- `query_order(order_id)` - Check status
- `reconcile()` - Reconcile state

**Configuration:**
- `open_check_interval_secs` - Open order check interval
- `open_check_open_only` - Check only open orders
- `open_check_lookback_mins` - Lookback window for checks

### 10.3 State Persistence

**Redis Backend:**
- Order state persistence
- Position state persistence
- Account state persistence
- Strategy state persistence
- Instrument definitions

**PostgreSQL Backend:**
- Alternative to Redis
- SQL queries for analysis
- Historical data storage

**Configuration:**
```python
cache_database = CacheDatabaseConfig(
    type="redis",
    host="localhost",
    port=6379,
)
```

---

## XI. ADAPTERS & INTEGRATIONS

### 11.1 Supported Integrations

#### **Cryptocurrency Exchanges**
- **Binance** - Spot, Futures, US
  - ID: BINANCE
  - Type: Crypto Exchange
  - Status: Stable
  
- **Bybit** - Spot, Linear, Inverse
  - ID: BYBIT
  - Type: Crypto Exchange
  - Status: Stable

- **OKX** - Spot, Futures, Options
  - ID: OKX
  - Type: Crypto Exchange
  - Status: Stable

- **dYdX** - Decentralized perpetuals
  - ID: DYDX
  - Type: Crypto Exchange
  - Status: Stable

- **Coinbase International**
  - ID: COINBASE_INTX
  - Type: Crypto Exchange
  - Status: Stable

- **Kraken** - Spot
  - ID: KRAKEN
  - Type: Crypto Exchange
  - Status: Stable (added v1.222.0)

- **Polymarket** - Prediction markets
  - ID: POLYMARKET
  - Type: Betting Exchange
  - Status: Beta

#### **Traditional Markets**
- **Interactive Brokers** - Multi-asset
  - ID: INTERACTIVE_BROKERS
  - Type: Brokerage
  - Status: Stable

#### **Data Providers**
- **Databento** - Market data
  - ID: DATABENTO
  - Type: Data Provider
  - Status: Stable

- **Tardis** - Historical crypto data
  - ID: TARDIS
  - Type: Data Provider
  - Status: Stable

#### **Betting Exchanges**
- **Betfair** - Sports betting
  - ID: BETFAIR
  - Type: Betting Exchange
  - Status: Stable

### 11.2 Adapter Architecture

**Rust Core:**
- HTTP client with rate limiting
- WebSocket client with auto-reconnect
- Data parsing and normalization
- Performance-critical operations

**Python Layer:**
- Integration with NautilusTrader engines
- Configuration management
- Error handling
- Logging

**Common Adapter Pattern:**
```
nautilus_trader/adapters/{venue}/
├── common/           # Shared types and enums
├── http/             # HTTP client
├── websocket/        # WebSocket client  
├── parsing/          # Data parsing
├── providers.py      # Instrument provider
├── data.py           # Data client
├── execution.py      # Execution client
└── config.py         # Configuration
```

### 11.3 Adapter Implementation

**Development Order:**
1. **HTTP Client** - Basic API communication
2. **Instrument Provider** - Load instrument definitions
3. **Data Client** - Market data subscriptions
4. **Execution Client** - Order management

**Best Practices:**
- Use `ustr::Ustr` for repeated strings
- Implement dual-tier cache (DashMap + AHashMap)
- Standardize method names (cache_instruments, get_instrument)
- Separate parsing logic in factories.rs

---

## XII. REPORTS & ANALYTICS

### 12.1 Report Types

#### **ReportProvider** (Static Methods)

**Order Reports:**
- `generate_orders_report(orders)` - All order details
- `generate_order_fills_report(orders)` - One row per order with fills
- `generate_fills_report(orders)` - One row per fill event

**Position Reports:**
- `generate_positions_report(positions)` - Position summary
- `generate_account_report(account, start, end)` - Account state over time

**Output Format:**
All reports return pandas DataFrames.

### 12.2 Performance Statistics

**Available via PortfolioAnalyzer:**

#### **PnL Statistics**
- Total PnL
- Total PnL Percentage
- Gross PnL
- Net PnL
- Win Rate
- Loss Rate
- Profit Factor
- Average Win
- Average Loss
- Max Winner
- Max Loser
- Expectancy
- Expectancy Percentage

#### **Return Statistics**
- Total Return
- Annualized Return (CAGR)
- Daily/Monthly/Yearly Returns
- Sharpe Ratio
- Sortino Ratio
- Calmar Ratio
- Information Ratio
- Maximum Drawdown
- Maximum Drawdown Duration
- Drawdown Recovery Time

#### **Position Statistics**
- Total Positions
- Win Count / Loss Count
- Long Count / Short Count
- Average Win Duration
- Average Loss Duration
- Average Position Duration

#### **Order Statistics**
- Total Orders
- Total Fills
- Fill Rate
- Average Fill Size
- Average Slippage

### 12.3 Visualization

**Tearsheet Generation:**
```python
from nautilus_trader.analysis import Tearsheet

tearsheet = Tearsheet(
    charts=["equity", "drawdown", "monthly_returns"],
    theme="nautilus",
    title="Strategy Performance"
)

tearsheet.create(
    account_balances=balances,
    positions=positions,
    fills=fills
)
```

**Available Charts:**
- `stats_table` - Performance statistics table
- `equity` - Equity curve
- `drawdown` - Drawdown chart
- `monthly_returns` - Monthly return heatmap
- `distribution` - Return distribution
- `rolling_sharpe` - Rolling Sharpe ratio
- `yearly_returns` - Yearly return bars
- `bars_with_fills` - Price bars with fill markers

**Themes:**
- `plotly_white` (default)
- `plotly_dark`
- `nautilus` (custom theme)

---

## XIII. MESSAGE BUS

### 13.1 Architecture

**Purpose:**
- Decouples components
- Routes messages between actors
- Enables pub/sub pattern
- Maintains event order

**Message Types:**
1. **Data** - Market data and custom data
2. **Commands** - Trading commands (submit, modify, cancel)
3. **Events** - State changes and notifications
4. **Requests** - Data requests
5. **Responses** - Request responses

### 13.2 MessageBus Methods

**Publishing:**
- `publish(topic, message)` - Publish message to topic
- `publish_data(data_type, data)` - Publish data
- `send(endpoint, message)` - Send to specific endpoint

**Subscribing:**
- `subscribe(topic, handler, priority=0)` - Subscribe to topic
- `unsubscribe(topic, handler)` - Unsubscribe

**Request/Response:**
- `request(endpoint, request)` - Send request
- `response(request_id, response)` - Send response

**Topics:**
- Data topics: `data.{data_type}`
- Event topics: `events.{event_type}`
- Command topics: `commands.{command_type}`

---

## XIV. CLOCK & TIMING

### 14.1 Clock Implementations

**TestClock:**
- Manual time control
- For backtesting
- Nanosecond precision
- Deterministic

**LiveClock:**
- System time
- For live trading
- Nanosecond precision
- Real-time

### 14.2 Clock Methods

**Timestamps:**
- `utc_now()` - Current UTC as pd.Timestamp
- `timestamp_ns()` - Current time as nanoseconds since epoch
- `timestamp_ms()` - Current time as milliseconds since epoch
- `timestamp_us()` - Current time as microseconds since epoch

**Time Alerts:**
- `set_time_alert(name, alert_time, callback=None)` - One-time alert
- `cancel_time_alert(name)` - Cancel alert

**Timers:**
- `set_timer(name, interval, start_time=None, stop_time=None, callback=None)` - Recurring timer
- `cancel_timer(name)` - Cancel specific timer
- `cancel_timers()` - Cancel all timers

**Timer Names:**
Unique string identifiers for each timer/alert.

---

## XV. LOGGING

### 15.1 Logging System

**Log Levels:**
- DEBUG - Detailed diagnostic information
- INFO - General information
- WARNING - Warning messages
- ERROR - Error messages
- CRITICAL - Critical failures

**Configuration:**
```python
from nautilus_trader.config import LoggingConfig

logging = LoggingConfig(
    log_level="INFO",
    log_level_file="DEBUG",
    log_file_format="json",
    log_colors=True,
    bypass_logging=False
)
```

### 15.2 Logger Methods

**Available in Components:**
- `self.log.debug(msg, color=None)` - Debug message
- `self.log.info(msg, color=None)` - Info message
- `self.log.warning(msg, color=None)` - Warning message
- `self.log.error(msg, color=None)` - Error message
- `self.log.critical(msg, color=None)` - Critical message

**Color Options:**
- `NORMAL`, `GREEN`, `BLUE`, `MAGENTA`, `CYAN`, `YELLOW`, `RED`

**Special Features:**
- Structured logging (JSON format)
- File rotation
- Per-component log levels
- Color-coded console output
- Event suppression

---

## XVI. SERIALIZATION

### 16.1 Supported Formats

**MessagePack:**
- Binary format
- Compact size
- Fast serialization
- Default for persistence

**JSON:**
- Human-readable
- Debugging friendly
- Larger size

**Cap'n Proto:**
- Zero-copy serialization
- Extremely fast
- Opt-in via `capnp` feature flag
- Added in v1.222.0

### 16.2 Serializable Objects

**All domain objects support serialization:**
- Orders
- Events
- Positions
- Instruments
- Data objects
- Configurations

**Methods:**
- `to_dict()` - Convert to dictionary
- `to_json()` - Serialize to JSON
- `from_dict(dict)` - Deserialize from dict
- `from_json(json)` - Deserialize from JSON

---

## XVII. IDENTIFIERS

### 17.1 Core Identifiers

**TraderId:**
- Unique trader instance identifier
- Format: `{name}-{instance_id}`
- Example: `TRADER-001`

**StrategyId:**
- Unique strategy identifier
- Format: `{class_name}-{order_id_tag}`
- Example: `EMACross-001`

**ComponentId:**
- Generic component identifier
- Base for ActorId, StrategyId, ExecAlgorithmId

**VenueId:**
- Trading venue identifier
- Examples: `BINANCE`, `INTERACTIVE_BROKERS`

**InstrumentId:**
- Instrument identifier
- Format: `{symbol}.{venue}`
- Example: `ETHUSDT-PERP.BINANCE`

**ClientId:**
- Data/execution client identifier
- Examples: `BINANCE-001`, `IBKR-001`

**AccountId:**
- Trading account identifier
- Format: `{name}-{number}.{venue}`
- Example: `IB-U123456.INTERACTIVE_BROKERS`

**ClientOrderId:**
- Client-side order identifier
- Format: `{strategy_id}-{order_count}-{timestamp}`
- Example: `EMACross-001-1-1234567890`

**VenueOrderId:**
- Venue-assigned order identifier
- Opaque string from venue

**PositionId:**
- Position identifier
- Format depends on OMS type:
  - HEDGING: Unique per position
  - NETTING: Based on instrument

**TradeId:**
- Individual fill/trade identifier
- Venue-assigned or generated

### 17.2 Identifier Properties

**Immutable:**
All identifiers are immutable value objects.

**Hashable:**
Can be used as dictionary keys and set members.

**String Conversion:**
- `str(identifier)` - String representation
- `identifier.value` - Raw string value

**Parsing:**
Most identifiers support `from_str()` class method:
```python
instrument_id = InstrumentId.from_str("BTCUSDT.BINANCE")
```

---

## XVIII. VALUE TYPES

### 18.1 Price & Quantity

**Price:**
- Fixed-point decimal price
- Specified precision
- Immutable value object
- Arithmetic operations supported

**Quantity:**
- Fixed-point decimal quantity
- Specified precision
- Immutable value object
- Arithmetic operations supported

**Methods:**
- `make_price(value)` - Create price from instrument
- `make_qty(value)` - Create quantity from instrument
- `as_double()` - Convert to double
- `as_decimal()` - Convert to Decimal

### 18.2 Money

**Money:**
- Amount with currency
- Fixed-point precision
- Immutable value object

**Properties:**
- `amount` - Decimal amount
- `currency` - Currency object
- `as_double()` - Double representation
- `as_decimal()` - Decimal representation

**Arithmetic:**
Supports +, -, *, / with same currency.

### 18.3 Currency

**Currency:**
- ISO 4217 currency code
- Precision (decimal places)
- Currency type (FIAT, CRYPTO, COMMODITY)

**Built-in Currencies:**
- Fiat: USD, EUR, GBP, JPY, etc.
- Crypto: BTC, ETH, USDT, USDC, etc.
- Commodities: XAU (gold), XAG (silver)

### 18.4 TimeInForce

**Enum Values:**
- `GTC` - Good 'til canceled
- `IOC` - Immediate or cancel
- `FOK` - Fill or kill
- `GTD` - Good 'til date
- `DAY` - Day order
- `AT_THE_OPEN` - At market open
- `AT_THE_CLOSE` - At market close

### 18.5 OrderSide

**Enum Values:**
- `BUY` - Buy order
- `SELL` - Sell order
- `NO_ORDER_SIDE` - Undefined

### 18.6 OrderType

**Enum Values:**
- `MARKET` - Market order
- `LIMIT` - Limit order
- `STOP_MARKET` - Stop market
- `STOP_LIMIT` - Stop limit
- `MARKET_TO_LIMIT` - Market-to-limit
- `MARKET_IF_TOUCHED` - Market if touched
- `LIMIT_IF_TOUCHED` - Limit if touched
- `TRAILING_STOP_MARKET` - Trailing stop market
- `TRAILING_STOP_LIMIT` - Trailing stop limit

### 18.7 PositionSide

**Enum Values:**
- `LONG` - Long position
- `SHORT` - Short position
- `FLAT` - No position

---

## XIX. INSTRUMENTS

### 19.1 Instrument Types

**Base Instrument:**
Abstract base for all instruments with common properties.

**Instrument Subtypes:**
- `CurrencyPair` - FX spot pairs (EUR/USD)
- `CryptoPerpetual` - Crypto perpetual futures
- `CryptoFuture` - Crypto dated futures
- `Equity` - Stocks and shares
- `Future` - Traditional futures contracts
- `Option` - Options contracts
- `FuturesSpread` - Futures spreads
- `OptionsSpread` - Options spreads
- `OptionsChain` - Complete options chain
- `BettingInstrument` - Betting markets
- `SyntheticInstrument` - User-defined synthetic

### 19.2 Instrument Properties

**Common Properties:**
- `instrument_id` - Unique identifier
- `raw_symbol` - Venue-native symbol
- `asset_class` - FX, EQUITY, COMMODITY, CRYPTO, etc.
- `quote_currency` - Quote currency
- `is_inverse` - If inverse instrument
- `price_precision` - Price decimal places
- `size_precision` - Size decimal places
- `price_increment` - Minimum price tick
- `size_increment` - Minimum size tick
- `multiplier` - Contract multiplier
- `lot_size` - Lot size
- `max_quantity` - Maximum order quantity
- `min_quantity` - Minimum order quantity
- `max_notional` - Maximum notional value
- `min_notional` - Minimum notional value
- `max_price` - Maximum price
- `min_price` - Minimum price
- `margin_init` - Initial margin requirement
- `margin_maint` - Maintenance margin requirement
- `maker_fee` - Maker fee rate
- `taker_fee` - Taker fee rate
- `ts_event` - Event timestamp
- `ts_init` - Initialization timestamp

### 19.3 Instrument Methods

**Price Calculations:**
- `make_price(value)` - Create valid price
- `make_qty(value)` - Create valid quantity
- `next_ask_price(value, num_ticks=0)` - Next valid ask price
- `next_bid_price(value, num_ticks=0)` - Next valid bid price
- `get_ask_prices(value, num_ticks=100)` - List of ask prices
- `get_bid_prices(value, num_ticks=100)` - List of bid prices

**Value Calculations:**
- `calculate_notional_value(qty, price, use_quote_for_inverse=False)` - Notional value

**Validation:**
- Automatic validation of price/quantity precision
- Raises `ValueError` for invalid values

---

## XX. CONFIGURATION

### 20.1 System Configuration

**NautilusConfig Base:**
All configuration classes inherit from `NautilusConfig`.

**Methods:**
- `dict()` - Dictionary representation
- `json()` - JSON serialization
- `json_primitives()` - JSON with primitives only
- `json_schema()` - Generate JSON schema
- `parse()` - Parse from JSON/dict
- `is_json_serializable()` - Check JSON compatibility
- `fully_qualified_name()` - Get class FQN
- `hash()` - Configuration hash

### 20.2 Core Configurations

**StrategyConfig:**
Base for strategy configurations.

**ActorConfig:**
Base for actor configurations.

**ExecAlgorithmConfig:**
Base for execution algorithm configurations.

**DataEngineConfig:**
- `time_bars_build_with_no_updates` - Build bars without updates
- `time_bars_timestamp_on_close` - Timestamp bars on close
- `validate_data_sequence` - Validate data ordering

**ExecEngineConfig:**
- `load_cache` - Load state from cache on startup
- `allow_cash_positions` - Allow cash positions
- `debug` - Enable debug mode

**RiskEngineConfig:**
- `bypass` - Bypass risk checks (dangerous!)
- `max_order_submit_rate` - Maximum order submission rate
- `max_order_modify_rate` - Maximum order modification rate
- `max_notional_per_order` - Maximum notional per order

**CacheDatabaseConfig:**
- `type` - Database type (redis, postgres)
- `host` - Database host
- `port` - Database port
- `username` - Username
- `password` - Password

**LoggingConfig:**
- `log_level` - Console log level
- `log_level_file` - File log level
- `log_directory` - Log file directory
- `log_file_format` - Format (text, json)
- `log_colors` - Enable colored output
- `bypass_logging` - Disable logging

### 20.3 Adapter Configurations

**Example: Binance Configuration**
```python
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig

config = BinanceDataClientConfig(
    api_key="your_api_key",
    api_secret="your_api_secret",
    account_type="futures_usdt",  # spot, futures_usdt, futures_coin
    testnet=False,
    base_url_http=None,  # Override HTTP endpoint
    base_url_ws=None,  # Override WebSocket endpoint
)
```

**Common Adapter Config Options:**
- `api_key` - API key
- `api_secret` - API secret
- `testnet` - Use testnet/sandbox
- `base_url_http` - HTTP endpoint override
- `base_url_ws` - WebSocket endpoint override

---

## XXI. OPTIMIZATION TRICKS & BEST PRACTICES

### 21.1 Performance Optimizations

**Rust Core:**
1. **Critical components in Rust** for maximum performance
2. **Circular buffers** for indicators (bounded memory)
3. **Zero-copy operations** where possible
4. **ArrayDeque** instead of VecDeque for fixed capacity
5. **Cap'n Proto** for zero-copy serialization (opt-in)

**Data Loading:**
1. **Pre-sort data** before adding to BacktestEngine
2. **Use sort=False** when data is already sorted
3. **Batch data loading** for multiple instruments
4. **Stream large datasets** with ParquetDataCatalog
5. **Use Parquet format** for storage (columnar, compressed)

**Memory Management:**
1. **Configure cache limits** based on requirements
2. **Use purge methods** to clean old data
3. **Enable database persistence** for long-running systems
4. **Limit bar/tick retention** in cache

**Indicators:**
1. **Register indicators** to receive automatic updates
2. **Use Rust implementations** over Python when available
3. **Avoid unnecessary indicator calculations**
4. **Reset indicators** when strategy resets

**Order Management:**
1. **Use order emulation** for advanced order types
2. **Batch order submissions** when possible
3. **Use GTD management** to reduce venue load
4. **Enable reconciliation** for live trading

### 21.2 Code Organization

**Strategy Development:**
1. **Separate configuration** from logic
2. **Use StrategyConfig** for all parameters
3. **Unique order_id_tag** for multiple instances
4. **Implement on_save/on_load** for state persistence

**Component Design:**
1. **Use Actor** for non-trading components
2. **Use Strategy** for trading logic
3. **Use ExecAlgorithm** for execution logic
4. **Publish signals** from actors to strategies

**Error Handling:**
1. **Handle exceptions** in event handlers
2. **Use try-catch** around risky operations
3. **Log errors** with appropriate levels
4. **Implement on_fault** for degraded mode

### 21.3 Testing

**Backtesting:**
1. **Start with bar data** for rapid iteration
2. **Progress to tick data** for accuracy
3. **Use order book data** for market making
4. **Validate with multiple data sources**

**Live Trading:**
1. **Test on sandbox first** (paper trading)
2. **Start with small position sizes**
3. **Monitor reconciliation** closely
4. **Enable comprehensive logging**
5. **Use state persistence** (Redis/PostgreSQL)

**Validation:**
1. **Check indicator initialization** before using
2. **Validate data timestamps** are sequential
3. **Monitor cache updates** for stale data
4. **Compare backtest vs live** behavior

### 21.4 Risk Management

**Pre-trade Controls:**
1. **Configure RiskEngine** limits
2. **Set max order size** per instrument
3. **Set max notional** exposure
4. **Enable order rate limits**

**Position Management:**
1. **Use stop losses** for all positions
2. **Implement position sizing** logic
3. **Monitor margin** requirements
4. **Track unrealized PnL** continuously

**Monitoring:**
1. **Set up health checks** for live systems
2. **Monitor order fill rates**
3. **Track slippage** metrics
4. **Alert on unusual** behavior

### 21.5 Debugging

**Logging:**
1. **Set appropriate log levels** (DEBUG for development)
2. **Use structured logging** (JSON format)
3. **Log state changes** in strategies
4. **Color-code** console output

**Analysis:**
1. **Generate reports** after backtests
2. **Review order fills** for slippage
3. **Analyze position** durations
4. **Check indicator** values

**Tools:**
1. **Use BacktestNode** for high-level API
2. **Inspect Cache** for current state
3. **Review MessageBus** subscriptions
4. **Monitor Portfolio** metrics

---

## XXII. SUMMARY OF ALL METHODS

### Strategy/Actor Methods (300+)

#### Data Subscription (30+ methods)
- subscribe_bars, subscribe_quote_ticks, subscribe_trade_ticks
- subscribe_order_book_deltas, subscribe_order_book_snapshots
- subscribe_instrument, subscribe_instrument_status, subscribe_instrument_close
- subscribe_data, subscribe_signals
- unsubscribe_* (matching unsubscribe methods)

#### Data Requests (15+ methods)
- request_bars, request_quote_ticks, request_trade_ticks
- request_instrument, request_instruments
- request_data

#### Order Management (25+ methods)
- submit_order, submit_order_list
- modify_order, cancel_order, cancel_orders, cancel_all_orders
- close_position, close_all_positions
- query_order, query_position

#### Cache Access (100+ methods)
- quote_tick, trade_tick, bar, order_book
- order, orders, orders_open, orders_closed
- position, positions, positions_open, positions_closed
- account, accounts, instrument, instruments
- [Many more cache retrieval methods]

#### Portfolio Access (25+ methods)
- unrealized_pnl, realized_pnl, net_exposure, net_position
- is_net_long, is_net_short, is_flat, is_completely_flat
- balances_locked, margins_init, margins_maint
- [Additional portfolio methods]

#### Timer/Task Management (15+ methods)
- set_time_alert, set_timer, cancel_timer, cancel_timers
- create_task, run_in_executor, queue_for_executor
- cancel_task, cancel_all_tasks

#### Indicator Management (5+ methods)
- register_indicator_for_bars
- register_indicator_for_quote_ticks
- register_indicator_for_trade_ticks

#### Component Lifecycle (10+ methods)
- start, stop, resume, reset, dispose
- degrade, fault, save, load

#### Event Handlers (50+ methods)
All on_* methods for data, orders, positions, events

---

## XXIII. FUNCTION USAGE STATUS

### Commonly Used Functions ✓

**Data Handling:**
- ✓ subscribe_bars - Subscribe to bar data
- ✓ subscribe_quote_ticks - Subscribe to quotes
- ✓ request_bars - Request historical bars
- ✓ on_bar - Handle bar updates
- ✓ on_quote_tick - Handle quote updates

**Order Management:**
- ✓ submit_order - Submit orders
- ✓ modify_order - Modify orders
- ✓ cancel_order - Cancel orders
- ✓ order_factory.limit - Create limit orders
- ✓ order_factory.market - Create market orders

**Cache Access:**
- ✓ cache.instrument - Get instrument
- ✓ cache.order - Get order
- ✓ cache.position - Get position
- ✓ cache.quote_tick - Last quote
- ✓ cache.bar - Last bar

**Portfolio:**
- ✓ portfolio.unrealized_pnl - Unrealized P&L
- ✓ portfolio.realized_pnl - Realized P&L
- ✓ portfolio.account - Get account
- ✓ portfolio.is_flat - Check if flat

**Lifecycle:**
- ✓ on_start - Strategy initialization
- ✓ on_stop - Strategy cleanup
- ✓ register_indicator_for_bars - Register indicators

### Less Commonly Used Functions ○

**Advanced Orders:**
- ○ submit_order_list - Bracket/OCO orders
- ○ order_factory.trailing_stop_market - Trailing stops
- ○ order_factory.stop_limit - Stop limit orders

**Advanced Data:**
- ○ subscribe_order_book_deltas - Order book updates
- ○ subscribe_instrument_status - Status updates
- ○ on_order_book - Order book handler
- ○ on_instrument_status - Status handler

**State Management:**
- ○ on_save - Save strategy state
- ○ on_load - Load strategy state
- ○ on_resume - Resume from pause
- ○ on_degrade - Degraded mode

**Advanced Cache:**
- ○ cache.orders_inflight - Inflight orders
- ○ cache.orders_emulated - Emulated orders
- ○ cache.position_snapshots - Position snapshots

**Advanced Portfolio:**
- ○ portfolio.margins_init - Initial margins
- ○ portfolio.margins_maint - Maintenance margins
- ○ portfolio.balances_locked - Locked balances
- ○ portfolio.net_exposures - Net exposures

**Task Management:**
- ○ run_in_executor - Thread pool execution
- ○ queue_for_executor - Sequential tasks
- ○ create_task - Async tasks

### Rarely Used Functions △

**Exotic Orders:**
- △ order_factory.market_if_touched - MIT orders
- △ order_factory.limit_if_touched - LIT orders
- △ order_factory.market_to_limit - MTL orders

**Specialized Data:**
- △ subscribe_instrument_close - Session close
- △ on_instrument_close - Close handler
- △ on_historical_data - Historical data handler
- △ subscribe_signals - Signal subscription

**Component Management:**
- △ deregister_warning_event - Event filtering
- △ register_executor - Executor registration
- △ fully_qualified_name - Get class FQN

**Advanced Reconciliation:**
- △ query_order - Manual order query
- △ check_residuals - Check for orphaned data
- △ reconcile - Manual reconciliation

---

## XXIV. IMPLEMENTATION EXAMPLES

### Example 1: Simple EMA Cross Strategy

```python
from decimal import Decimal
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.model import InstrumentId, BarType, OrderSide

class EMACrossConfig(StrategyConfig):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_period: int = 10
    slow_period: int = 20
    trade_size: Decimal

class EMACrossStrategy(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)
        
    def on_start(self):
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.request_bars(self.config.bar_type)
        self.subscribe_bars(self.config.bar_type)
        
    def on_bar(self, bar):
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return
            
        if self.fast_ema.value > self.slow_ema.value:
            if not self.portfolio.is_net_long(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=self.config.trade_size
                )
                self.submit_order(order)
        elif self.fast_ema.value < self.slow_ema.value:
            if not self.portfolio.is_net_short(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.SELL,
                    quantity=self.config.trade_size
                )
                self.submit_order(order)
```

### Example 2: Backtest Setup

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.persistence.catalog import ParquetDataCatalog

# Load data
catalog = ParquetDataCatalog("./data")

# Configure backtest
config = BacktestEngineConfig(
    trader_id="BACKTESTER-001",
    logging=LoggingConfig(log_level="ERROR"),
)

# Create and run backtest
node = BacktestNode(configs=[config])

# Add strategies
node.add_strategy(EMACrossStrategy(
    config=EMACrossConfig(
        instrument_id="ETHUSDT-PERP.BINANCE",
        bar_type="ETHUSDT-PERP.BINANCE-1-MINUTE[LAST]-EXTERNAL",
        trade_size=Decimal("1.0"),
        order_id_tag="001"
    )
))

# Run
node.run()

# Analyze results
engine = node.kernel.get_engine()
stats = engine.portfolio.analyzer.get_performance_stats_pnls()
print(stats)
```

### Example 3: Live Trading Setup

```python
from nautilus_trader.live.node import TradingNode
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
from nautilus_trader.adapters.binance.config import BinanceExecClientConfig

# Configure live trading
config = TradingNodeConfig(
    trader_id="TRADER-001",
    data_clients={
        "BINANCE": BinanceDataClientConfig(
            api_key="your_key",
            api_secret="your_secret",
            account_type="futures_usdt",
        )
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(
            api_key="your_key",
            api_secret="your_secret",
            account_type="futures_usdt",
        )
    },
    timeout_connection=20.0,
    timeout_reconciliation=10.0,
    timeout_portfolio=10.0,
    timeout_disconnection=10.0,
)

# Create trading node
node = TradingNode(config=config)

# Add strategies
node.add_strategy(EMACrossStrategy(config))

# Start trading
node.start()
```

---

## XXV. CONCLUSION

NautilusTrader is a comprehensive, production-grade algorithmic trading platform that provides:

1. **Unified Codebase**: Same strategy code for backtesting and live trading
2. **High Performance**: Rust core with Python bindings for optimal speed
3. **Comprehensive Features**: 300+ methods across all components
4. **Multiple Asset Classes**: FX, Equities, Futures, Options, Crypto, Betting
5. **Extensive Integrations**: 15+ venue adapters with more in development
6. **Advanced Analytics**: Built-in performance metrics and reporting
7. **Flexible Architecture**: Modular design with custom component support
8. **Professional Grade**: Used in production by quantitative trading firms

The library excels at providing institutional-grade infrastructure for algorithmic trading while maintaining accessibility through its Python API. The Rust core ensures performance critical operations run at native speeds, while the event-driven architecture provides accurate simulation and real-time execution capabilities.

---

**Documentation Version**: Based on NautilusTrader 0.52.0 (Latest)  
**Last Updated**: February 2026  
**Total Methods Documented**: 300+  
**Total Components**: 50+  
**Supported Integrations**: 15+

"""
Backtesting Engine — runs BaseStrategy subclasses against historical bar data.
Reference: PAPER_TRADING_BACKTESTING_GUIDE.md, IMPLEMENTATION_ROADMAP.md §Phase 3

Design decisions:
- Works with the project's own BaseStrategy (not Nautilus Strategy).
- Simulates fills with configurable slippage and commissions.
- Produces comprehensive performance metrics (Sharpe, drawdown, win rate).
- Keeps a complete trade log and equity curve for analysis.
"""

import logging
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Configuration & Result data classes
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    initial_capital: float = 100_000.0
    commission_pct: float = 0.001       # 0.1% per trade (brokerage + charges)
    slippage_pct: float = 0.0005        # 0.05% slippage per trade
    lot_size: int = 1                   # Minimum trade lot
    max_position_size: int = 100        # Maximum position in units
    risk_free_rate: float = 0.06        # 6% annual (Indian market)


@dataclass
class Trade:
    """Record of a single trade execution."""

    timestamp: str
    side: str               # "BUY" or "SELL"
    quantity: int
    price: float             # Execution price (after slippage)
    commission: float
    pnl: float = 0.0        # Realized P&L for closing trades
    cumulative_pnl: float = 0.0


@dataclass
class BacktestResult:
    """Complete results of a backtest run."""

    # Summary
    strategy_name: str = ""
    start_date: str = ""
    end_date: str = ""
    total_bars: int = 0

    # Performance
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return_pct: float = 0.0
    total_pnl: float = 0.0
    total_commission: float = 0.0

    # Risk metrics
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_duration: int = 0   # bars

    # Trade statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Data
    trade_log: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable summary string."""
        return (
            f"═══ Backtest Results: {self.strategy_name} ═══\n"
            f"  Period      : {self.start_date} → {self.end_date} ({self.total_bars} bars)\n"
            f"  Capital     : ₹{self.initial_capital:,.2f} → ₹{self.final_capital:,.2f}\n"
            f"  Return      : {self.total_return_pct:+.2f}%\n"
            f"  P&L         : ₹{self.total_pnl:,.2f}  (commission: ₹{self.total_commission:,.2f})\n"
            f"  Sharpe      : {self.sharpe_ratio:.3f}\n"
            f"  Max DD      : {self.max_drawdown_pct:.2f}%\n"
            f"  Trades      : {self.total_trades} (W:{self.winning_trades} L:{self.losing_trades})\n"
            f"  Win Rate    : {self.win_rate:.1f}%\n"
            f"  Profit Fac. : {self.profit_factor:.2f}\n"
            f"  Avg Win/Loss: ₹{self.avg_win:,.2f} / ₹{self.avg_loss:,.2f}\n"
        )


# ═══════════════════════════════════════════════════════════════════════
# Backtest Engine
# ═══════════════════════════════════════════════════════════════════════


class BacktestEngine:
    """
    Backtesting engine that feeds historical bars to a BaseStrategy
    and simulates order fills.

    Usage:
        from src.strategies.ema_crossover import EMACrossoverStrategy
        from src.data.data_manager import HistoricalDataManager

        strategy = EMACrossoverStrategy({"fast_period": 9, "slow_period": 21, "quantity": 10})
        data = HistoricalDataManager.create_sample_data(days=120)

        engine = BacktestEngine(strategy, data)
        result = engine.run()
        print(result.summary())
    """

    def __init__(
        self,
        strategy,
        data: pd.DataFrame,
        config: BacktestConfig = None,
    ):
        """
        Args:
            strategy: An instance of BaseStrategy (or subclass)
            data: DataFrame with columns: timestamp, open, high, low, close, volume
            config: Backtest configuration (defaults used if None)
        """
        self.strategy = strategy
        self.data = data.copy()
        self.config = config or BacktestConfig()

        # Execution state
        self._capital = self.config.initial_capital
        self._position = 0
        self._entry_price = 0.0
        self._realized_pnl = 0.0
        self._total_commission = 0.0
        self._trade_log: List[Trade] = []
        self._equity_curve: List[float] = []
        self._round_trip_pnls: List[float] = []  # For win/loss stats

        # Wire up the strategy's order callback to our simulated fills
        self.strategy.set_order_callback(self._handle_order)

        # Patch strategy to bypass market-hours check during backtesting
        self._patch_strategy_for_backtest()

    def _patch_strategy_for_backtest(self):
        """
        Override strategy's submit_order to bypass is_market_open() check.
        In backtesting, we process historical bars that may be outside current
        market hours, so the live-trading guard must be disabled.
        """
        strategy = self.strategy

        def backtest_submit_order(side: str, quantity: int, order_type: str = "MARKET", price: float = 0):
            if strategy._order_callback:
                strategy._order_callback({
                    "strategy": strategy.name,
                    "instrument_id": strategy.instrument_id,
                    "side": side,
                    "quantity": quantity,
                    "order_type": order_type,
                    "price": price,
                })

        strategy.submit_order = backtest_submit_order

    # ─── Main Run Loop ───────────────────────────────────────────────

    def run(self) -> BacktestResult:
        """
        Execute the backtest: iterate over all bars and produce results.

        Returns:
            BacktestResult with all metrics, trade log, and equity curve.
        """
        logger.info(f"🚀 Starting backtest: {self.strategy.name} | "
                     f"{len(self.data)} bars | Capital: ₹{self.config.initial_capital:,.2f}")

        # Call strategy on_start
        self.strategy.on_start()

        # Iterate bars
        for idx, row in self.data.iterrows():
            bar = {
                "timestamp": str(row.get("timestamp", idx)),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row.get("volume", 0)),
            }

            # Feed bar to strategy (this may trigger orders via callback)
            self.strategy.on_bar(bar)

            # Record equity (capital + mark-to-market of open position)
            mtm = self._position * bar["close"]
            equity = self._capital + mtm
            self._equity_curve.append(equity)

        # Force-close any open position at last bar's close
        if self._position != 0:
            last_close = float(self.data.iloc[-1]["close"])
            if self._position > 0:
                self._execute_fill("SELL", abs(self._position), last_close,
                                   str(self.data.iloc[-1].get("timestamp", "")))
            else:
                self._execute_fill("BUY", abs(self._position), last_close,
                                   str(self.data.iloc[-1].get("timestamp", "")))

        # Call strategy on_stop
        self.strategy.on_stop()

        # Build results
        result = self._compute_results()

        logger.info(f"✅ Backtest complete: {result.total_return_pct:+.2f}% | "
                     f"{result.total_trades} trades | Sharpe: {result.sharpe_ratio:.3f}")

        return result

    # ─── Order Handling ──────────────────────────────────────────────

    def _handle_order(self, order: Dict[str, Any]):
        """
        Callback wired to BaseStrategy.submit_order().
        Simulates immediate fill at the current bar's close with slippage.
        """
        side = order["side"]
        quantity = order.get("quantity", self.config.lot_size)

        # Clamp to max position size
        if abs(self._position + (quantity if side == "BUY" else -quantity)) > self.config.max_position_size:
            logger.debug(f"Position limit reached, order rejected: {side} {quantity}")
            return

        # Get current price (last bar close processed by strategy)
        # Use the most recent bar's close as the fill price base
        current_bar_idx = self.strategy.bar_count - 1
        if current_bar_idx < 0 or current_bar_idx >= len(self.data):
            return

        base_price = float(self.data.iloc[current_bar_idx]["close"])

        # Get timestamp
        ts = str(self.data.iloc[current_bar_idx].get("timestamp", current_bar_idx))

        self._execute_fill(side, quantity, base_price, ts)

    def _execute_fill(self, side: str, quantity: int, base_price: float, timestamp: str):
        """Simulate a fill with slippage and commission."""
        # Apply slippage
        if side == "BUY":
            fill_price = base_price * (1 + self.config.slippage_pct)
        else:
            fill_price = base_price * (1 - self.config.slippage_pct)

        # Calculate commission
        trade_value = fill_price * quantity
        commission = trade_value * self.config.commission_pct
        self._total_commission += commission

        # Calculate P&L for closing trades
        trade_pnl = 0.0
        if side == "BUY" and self._position < 0:
            # Closing short
            close_qty = min(quantity, abs(self._position))
            trade_pnl = (self._entry_price - fill_price) * close_qty - commission
            self._round_trip_pnls.append(trade_pnl)
        elif side == "SELL" and self._position > 0:
            # Closing long
            close_qty = min(quantity, self._position)
            trade_pnl = (fill_price - self._entry_price) * close_qty - commission
            self._round_trip_pnls.append(trade_pnl)
        else:
            # Opening trade — commission is a cost
            trade_pnl = -commission

        self._realized_pnl += trade_pnl

        # Update position
        if side == "BUY":
            if self._position <= 0:
                self._entry_price = fill_price
            self._position += quantity
            self._capital -= trade_value + commission
        else:
            if self._position >= 0:
                self._entry_price = fill_price
            self._position -= quantity
            self._capital += trade_value - commission

        # Update strategy position tracking
        self.strategy.update_position(side, quantity, fill_price)

        # Log trade
        trade = Trade(
            timestamp=timestamp,
            side=side,
            quantity=quantity,
            price=round(fill_price, 2),
            commission=round(commission, 2),
            pnl=round(trade_pnl, 2),
            cumulative_pnl=round(self._realized_pnl, 2),
        )
        self._trade_log.append(trade)

        logger.debug(f"  📋 {side} {quantity} @ {fill_price:.2f} | "
                      f"PnL={trade_pnl:+.2f} | Comm={commission:.2f}")

    # ─── Results Computation ─────────────────────────────────────────

    def _compute_results(self) -> BacktestResult:
        """Compute all performance metrics from trade log and equity curve."""
        result = BacktestResult()
        result.strategy_name = self.strategy.name
        result.initial_capital = self.config.initial_capital
        result.total_bars = len(self.data)
        result.total_commission = round(self._total_commission, 2)

        # Dates
        if "timestamp" in self.data.columns and len(self.data) > 0:
            result.start_date = str(self.data.iloc[0]["timestamp"])
            result.end_date = str(self.data.iloc[-1]["timestamp"])

        # Final capital and return
        result.final_capital = round(self._equity_curve[-1], 2) if self._equity_curve else self.config.initial_capital
        result.total_pnl = round(result.final_capital - result.initial_capital, 2)
        result.total_return_pct = round(
            (result.total_pnl / result.initial_capital) * 100, 2
        )

        # Trade statistics
        result.trade_log = self._trade_log
        result.equity_curve = [round(e, 2) for e in self._equity_curve]
        result.total_trades = len(self._trade_log)

        # Win/loss from round-trip P&Ls
        wins = [p for p in self._round_trip_pnls if p > 0]
        losses = [p for p in self._round_trip_pnls if p <= 0]

        result.winning_trades = len(wins)
        result.losing_trades = len(losses)

        total_round_trips = len(self._round_trip_pnls)
        result.win_rate = round(
            (result.winning_trades / total_round_trips * 100) if total_round_trips > 0 else 0, 1
        )

        result.avg_win = round(np.mean(wins), 2) if wins else 0.0
        result.avg_loss = round(np.mean(losses), 2) if losses else 0.0
        result.largest_win = round(max(wins), 2) if wins else 0.0
        result.largest_loss = round(min(losses), 2) if losses else 0.0

        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        result.profit_factor = round(
            (gross_profit / gross_loss) if gross_loss > 0 else float("inf"), 2
        )

        # Sharpe Ratio (annualized)
        if len(self._equity_curve) > 1:
            equity = np.array(self._equity_curve)
            returns = np.diff(equity) / equity[:-1]
            if returns.std() > 0:
                # Assume ~252 trading days, ~75 bars per day for 5-min intervals
                bars_per_year = 252 * 75
                excess_return = returns.mean() - (self.config.risk_free_rate / bars_per_year)
                result.sharpe_ratio = round(
                    excess_return / returns.std() * np.sqrt(bars_per_year), 3
                )

        # Max Drawdown
        if self._equity_curve:
            equity = np.array(self._equity_curve)
            peak = np.maximum.accumulate(equity)
            drawdown = (peak - equity) / peak * 100
            result.max_drawdown_pct = round(float(drawdown.max()), 2)

            # Drawdown duration (bars in drawdown)
            in_dd = drawdown > 0
            max_dur = 0
            current_dur = 0
            for dd in in_dd:
                if dd:
                    current_dur += 1
                    max_dur = max(max_dur, current_dur)
                else:
                    current_dur = 0
            result.max_drawdown_duration = max_dur

        return result

"""
Enhanced paper portfolio with P&L tracking, portfolio summary, and position limits.
Reference: SYSTEM_ARCHITECTURE.md §3.6
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.time_utils import now_ist
from src.observability.metrics import PORTFOLIO_VALUE, OPEN_POSITIONS, DAILY_PNL

logger = logging.getLogger(__name__)


class PaperPortfolio:
    """
    Simulates a portfolio for paper trading.
    Tracks cash, holdings, realized/unrealized P&L, and order history.
    """

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.holdings: Dict[str, Dict] = {}  # Symbol → {qty, avg_price, side}
        self.orders: List[Dict] = []

        # P&L tracking
        self.realized_pnl: float = 0.0
        self.daily_realized_pnl: float = 0.0
        self.trade_count: int = 0

    def execute_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
    ) -> Dict:
        """
        Execute a paper trade.
        Returns order result dict with status and details.
        """
        cost = quantity * price

        if side == "BUY":
            if cost > self.cash:
                logger.warning(f"⚠️ Insufficient funds: need ₹{cost:,.0f}, have ₹{self.cash:,.0f}")
                return {"status": "REJECTED", "reason": "INSUFFICIENT_FUNDS"}

            self.cash -= cost

            if symbol in self.holdings:
                # Average up/down
                h = self.holdings[symbol]
                old_qty = h["qty"]
                old_avg = h["avg_price"]
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + cost) / new_qty
                h["qty"] = new_qty
                h["avg_price"] = round(new_avg, 2)
            else:
                self.holdings[symbol] = {
                    "qty": quantity,
                    "avg_price": price,
                    "side": "LONG",
                    "product_type": product_type,
                    "entry_time": now_ist().isoformat(),
                }

        elif side == "SELL":
            if symbol in self.holdings:
                h = self.holdings[symbol]
                if quantity > h["qty"]:
                    logger.warning(f"⚠️ Insufficient qty: have {h['qty']}, want to sell {quantity}")
                    return {"status": "REJECTED", "reason": "INSUFFICIENT_QUANTITY"}

                # Calculate realized P&L
                pnl = (price - h["avg_price"]) * quantity
                self.realized_pnl += pnl
                self.daily_realized_pnl += pnl
                DAILY_PNL.set(self.daily_realized_pnl)

                self.cash += cost
                h["qty"] -= quantity

                if h["qty"] == 0:
                    del self.holdings[symbol]
            else:
                # Short sell (if allowed)
                self.holdings[symbol] = {
                    "qty": quantity,
                    "avg_price": price,
                    "side": "SHORT",
                    "product_type": product_type,
                    "entry_time": now_ist().isoformat(),
                }

        self.trade_count += 1

        # Record order
        order = {
            "order_id": f"PAPER-{self.trade_count:06d}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
            "product_type": product_type,
            "status": "COMPLETE",
            "timestamp": now_ist().isoformat(),
        }
        self.orders.append(order)
        OPEN_POSITIONS.set(len(self.holdings))

        logger.info(f"📄 Paper Trade: {side} {quantity} {symbol} @ ₹{price:,.2f} | "
                     f"Order #{order['order_id']}")

        return {
            "status": "COMPLETE",
            "order_id": order["order_id"],
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
        }

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value (Cash + Holdings at current prices)."""
        holdings_value = 0.0
        for symbol, data in self.holdings.items():
            price = current_prices.get(symbol, data["avg_price"])
            holdings_value += data["qty"] * price

        total = self.cash + holdings_value
        PORTFOLIO_VALUE.set(total)
        return total

    def get_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate unrealized P&L across all holdings."""
        pnl = 0.0
        for symbol, data in self.holdings.items():
            price = current_prices.get(symbol, data["avg_price"])
            if data["side"] == "LONG":
                pnl += (price - data["avg_price"]) * data["qty"]
            elif data["side"] == "SHORT":
                pnl += (data["avg_price"] - price) * data["qty"]
        return pnl

    def get_summary(self, current_prices: Dict[str, float] = None) -> Dict:
        """Get portfolio summary."""
        prices = current_prices or {}
        unrealized = self.get_unrealized_pnl(prices)
        portfolio_value = self.get_portfolio_value(prices)

        return {
            "initial_capital": self.initial_capital,
            "cash": round(self.cash, 2),
            "holdings_count": len(self.holdings),
            "portfolio_value": round(portfolio_value, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized, 2),
            "total_pnl": round(self.realized_pnl + unrealized, 2),
            "return_pct": round(((portfolio_value / self.initial_capital) - 1) * 100, 2),
            "trade_count": self.trade_count,
            "holdings": {
                sym: {
                    "qty": h["qty"],
                    "avg_price": h["avg_price"],
                    "side": h["side"],
                    "current_price": prices.get(sym, h["avg_price"]),
                    "pnl": round((prices.get(sym, h["avg_price"]) - h["avg_price"]) * h["qty"], 2),
                }
                for sym, h in self.holdings.items()
            },
        }

    def square_off_all(self, current_prices: Dict[str, float]) -> List[Dict]:
        """Square off all positions (used for MIS auto square-off)."""
        results = []
        for symbol in list(self.holdings.keys()):
            h = self.holdings[symbol]
            price = current_prices.get(symbol, h["avg_price"])
            side = "SELL" if h["side"] == "LONG" else "BUY"
            result = self.execute_order(symbol, side, h["qty"], price)
            results.append(result)
            logger.warning(f"🔄 Auto square-off: {side} {h['qty']} {symbol} @ ₹{price:,.2f}")
        return results

    def reset_daily(self):
        """Reset daily tracking (call at start of each trading day)."""
        self.daily_realized_pnl = 0.0

    def get_order_history(self, limit: int = 50) -> List[Dict]:
        """Get recent order history."""
        return self.orders[-limit:]

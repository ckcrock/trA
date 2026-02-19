"""
Bracket order manager — Entry + SL + Target with OCO logic.
Reference: SYSTEM_ARCHITECTURE.md §3.6
"""

import logging
import uuid
from typing import Dict, List, Optional, Callable
from src.utils.time_utils import now_ist

logger = logging.getLogger(__name__)


class BracketOrder:
    """Represents a single bracket order with entry, SL, and target legs."""

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        order_type: str = "LIMIT",
    ):
        self.id = f"BO-{uuid.uuid4().hex[:8].upper()}"
        self.symbol = symbol
        self.side = side        # BUY or SELL (entry side)
        self.quantity = quantity
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target = target
        self.order_type = order_type

        self.status = "PENDING"  # PENDING → ENTERED → COMPLETED / STOPPED_OUT
        self.entry_filled = False
        self.exit_side = "SELL" if side == "BUY" else "BUY"

        self.created_at = now_ist().isoformat()
        self.entered_at: Optional[str] = None
        self.exited_at: Optional[str] = None
        self.exit_reason: Optional[str] = None
        self.pnl: float = 0.0

    def check_entry(self, current_price: float) -> bool:
        """Check if entry condition is met (for LIMIT entry)."""
        if self.status != "PENDING":
            return False
        if self.side == "BUY" and current_price <= self.entry_price:
            return True
        if self.side == "SELL" and current_price >= self.entry_price:
            return True
        return False

    def check_exit(self, current_price: float) -> Optional[str]:
        """
        Check exit conditions (SL or target).
        Returns 'STOP_LOSS', 'TARGET', or None.
        """
        if self.status != "ENTERED":
            return None

        if self.side == "BUY":
            if current_price <= self.stop_loss:
                return "STOP_LOSS"
            if current_price >= self.target:
                return "TARGET"
        else:  # SELL entry
            if current_price >= self.stop_loss:
                return "STOP_LOSS"
            if current_price <= self.target:
                return "TARGET"

        return None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "status": self.status,
            "pnl": self.pnl,
            "created_at": self.created_at,
            "entered_at": self.entered_at,
            "exited_at": self.exited_at,
            "exit_reason": self.exit_reason,
        }


class BracketOrderManager:
    """
    Manages bracket orders:
    - Place bracket order (entry + SL + target)
    - Monitor entry fill
    - Auto-place SL and target on entry fill
    - OCO (one-cancels-other) for SL/target
    - Track P&L
    """

    def __init__(self):
        self.orders: Dict[str, BracketOrder] = {}
        self._order_callback: Optional[Callable] = None
        self.completed_orders: List[Dict] = []

    def set_order_callback(self, callback: Callable):
        """Set callback for order execution. Called with order dict."""
        self._order_callback = callback

    def place_bracket_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target: float,
        order_type: str = "LIMIT",
    ) -> str:
        """
        Place a bracket order.
        Returns the bracket order ID.
        """
        # Validate SL and target direction
        if side == "BUY":
            if stop_loss >= entry_price:
                logger.error("❌ BUY bracket: SL must be below entry")
                return ""
            if target <= entry_price:
                logger.error("❌ BUY bracket: target must be above entry")
                return ""
        else:
            if stop_loss <= entry_price:
                logger.error("❌ SELL bracket: SL must be above entry")
                return ""
            if target >= entry_price:
                logger.error("❌ SELL bracket: target must be below entry")
                return ""

        bo = BracketOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target=target,
            order_type=order_type,
        )
        self.orders[bo.id] = bo

        logger.info(
            f"📋 Bracket order placed: {bo.id} | {side} {quantity} {symbol} "
            f"entry=₹{entry_price:,.2f} SL=₹{stop_loss:,.2f} target=₹{target:,.2f}"
        )

        # If market order, immediately trigger entry
        if order_type == "MARKET":
            self._fill_entry(bo, entry_price)

        return bo.id

    def check_prices(self, symbol: str, current_price: float):
        """
        Check all bracket orders for a symbol against current price.
        Handles both entry and exit triggers.
        """
        for bo_id, bo in self.orders.items():
            if bo.symbol != symbol:
                continue

            # Check entry
            if bo.status == "PENDING" and bo.check_entry(current_price):
                self._fill_entry(bo, current_price)

            # Check exit (SL or target)
            elif bo.status == "ENTERED":
                exit_reason = bo.check_exit(current_price)
                if exit_reason:
                    self._fill_exit(bo, current_price, exit_reason)

    def _fill_entry(self, bo: BracketOrder, price: float):
        """Process entry fill."""
        bo.status = "ENTERED"
        bo.entry_filled = True
        bo.entered_at = now_ist().isoformat()

        logger.info(f"✅ Bracket entry filled: {bo.id} | {bo.side} @ ₹{price:,.2f}")

        if self._order_callback:
            self._order_callback({
                "symbol": bo.symbol,
                "side": bo.side,
                "quantity": bo.quantity,
                "price": price,
                "order_type": "MARKET",
                "source": "BRACKET_ENTRY",
                "bracket_id": bo.id,
            })

    def _fill_exit(self, bo: BracketOrder, price: float, reason: str):
        """Process exit fill (SL or target)."""
        bo.exited_at = now_ist().isoformat()
        bo.exit_reason = reason

        if bo.side == "BUY":
            bo.pnl = (price - bo.entry_price) * bo.quantity
        else:
            bo.pnl = (bo.entry_price - price) * bo.quantity

        bo.status = "COMPLETED" if reason == "TARGET" else "STOPPED_OUT"

        emoji = "🎯" if reason == "TARGET" else "🛑"
        logger.info(
            f"{emoji} Bracket exit: {bo.id} | {reason} @ ₹{price:,.2f} | "
            f"P&L: ₹{bo.pnl:,.2f}"
        )

        if self._order_callback:
            self._order_callback({
                "symbol": bo.symbol,
                "side": bo.exit_side,
                "quantity": bo.quantity,
                "price": price,
                "order_type": "MARKET",
                "source": f"BRACKET_{reason}",
                "bracket_id": bo.id,
            })

        self.completed_orders.append(bo.to_dict())

    def cancel(self, order_id: str) -> bool:
        """Cancel a bracket order (only if pending or entry not filled)."""
        bo = self.orders.get(order_id)
        if not bo:
            return False
        if bo.status == "PENDING":
            bo.status = "CANCELLED"
            logger.info(f"❌ Bracket cancelled: {order_id}")
            return True
        logger.warning(f"⚠️ Cannot cancel bracket {order_id} (status={bo.status})")
        return False

    def modify_sl(self, order_id: str, new_sl: float) -> bool:
        """Modify stop-loss of an active bracket order (trailing SL)."""
        bo = self.orders.get(order_id)
        if not bo or bo.status != "ENTERED":
            return False

        # Only allow moving SL in favorable direction
        if bo.side == "BUY" and new_sl > bo.stop_loss:
            bo.stop_loss = new_sl
            logger.info(f"📊 Bracket SL trailed: {order_id} → ₹{new_sl:,.2f}")
            return True
        elif bo.side == "SELL" and new_sl < bo.stop_loss:
            bo.stop_loss = new_sl
            logger.info(f"📊 Bracket SL trailed: {order_id} → ₹{new_sl:,.2f}")
            return True

        return False

    def get_active_orders(self, symbol: str = None) -> List[Dict]:
        """Get active bracket orders."""
        return [
            bo.to_dict()
            for bo in self.orders.values()
            if bo.status in ("PENDING", "ENTERED")
            and (symbol is None or bo.symbol == symbol)
        ]

    def get_completed_orders(self, limit: int = 50) -> List[Dict]:
        """Get completed bracket order history."""
        return self.completed_orders[-limit:]

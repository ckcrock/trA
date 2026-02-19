"""
GTT (Good Till Triggered) order engine.
Monitors prices and fires orders when trigger conditions are met.
Reference: SYSTEM_ARCHITECTURE.md §3.6
"""

import logging
import uuid
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from src.utils.time_utils import now_ist

logger = logging.getLogger(__name__)


class GTTOrder:
    """Represents a single GTT order."""

    def __init__(
        self,
        symbol: str,
        trigger_price: float,
        limit_price: float,
        quantity: int,
        side: str,
        condition: str = "GTE",  # GTE = trigger when >= , LTE = trigger when <=
    ):
        self.id = f"GTT-{uuid.uuid4().hex[:8].upper()}"
        self.symbol = symbol
        self.trigger_price = trigger_price
        self.limit_price = limit_price
        self.quantity = quantity
        self.side = side
        self.condition = condition
        self.status = "ACTIVE"
        self.created_at = now_ist().isoformat()
        self.triggered_at: Optional[str] = None

    def check_trigger(self, current_price: float) -> bool:
        """Check if the trigger condition is met."""
        if self.status != "ACTIVE":
            return False
        if self.condition == "GTE" and current_price >= self.trigger_price:
            return True
        if self.condition == "LTE" and current_price <= self.trigger_price:
            return True
        return False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "trigger_price": self.trigger_price,
            "limit_price": self.limit_price,
            "quantity": self.quantity,
            "side": self.side,
            "condition": self.condition,
            "status": self.status,
            "created_at": self.created_at,
            "triggered_at": self.triggered_at,
        }


class AdvancedOrderManager:
    """
    Manages GTT orders:
    - Place GTT with trigger condition (GTE/LTE)
    - Check triggers on every price update
    - Fire order callback when triggered
    - Support for OCO (One-Cancels-Other) pairs
    """

    def __init__(self):
        self.gtt_orders: Dict[str, GTTOrder] = {}
        self.oco_pairs: Dict[str, str] = {}  # order_id → linked_order_id
        self._order_callback: Optional[Callable] = None
        self.triggered_history: List[Dict] = []

    def set_order_callback(self, callback: Callable):
        """Set callback for when a GTT is triggered. Called with order dict."""
        self._order_callback = callback

    def place_gtt(
        self,
        symbol: str,
        trigger_price: float,
        limit_price: float,
        quantity: int,
        side: str = "BUY",
        condition: str = "GTE",
    ) -> str:
        """
        Place a GTT order.
        Returns the GTT order ID.
        """
        gtt = GTTOrder(
            symbol=symbol,
            trigger_price=trigger_price,
            limit_price=limit_price,
            quantity=quantity,
            side=side,
            condition=condition,
        )
        self.gtt_orders[gtt.id] = gtt
        logger.info(f"📋 GTT placed: {gtt.id} | {side} {quantity} {symbol} "
                     f"trigger={condition} ₹{trigger_price:,.2f} → limit ₹{limit_price:,.2f}")
        return gtt.id

    def place_oco(
        self,
        symbol: str,
        target_price: float,
        stop_loss_price: float,
        quantity: int,
    ) -> tuple:
        """
        Place OCO pair (target + stop-loss). When one triggers, the other cancels.
        Returns (target_id, stoploss_id).
        """
        target_id = self.place_gtt(
            symbol, target_price, target_price, quantity, "SELL", "GTE"
        )
        sl_id = self.place_gtt(
            symbol, stop_loss_price, stop_loss_price, quantity, "SELL", "LTE"
        )
        self.oco_pairs[target_id] = sl_id
        self.oco_pairs[sl_id] = target_id
        logger.info(f"🔗 OCO pair: target={target_id}, SL={sl_id}")
        return target_id, sl_id

    def cancel_gtt(self, order_id: str) -> bool:
        """Cancel a GTT order."""
        gtt = self.gtt_orders.get(order_id)
        if not gtt or gtt.status != "ACTIVE":
            return False
        gtt.status = "CANCELLED"
        logger.info(f"❌ GTT cancelled: {order_id}")
        return True

    def check_triggers(self, symbol: str, current_price: float):
        """
        Check all GTT orders for a symbol against current price.
        Fire callbacks for triggered orders.
        """
        triggered = []

        for gtt_id, gtt in self.gtt_orders.items():
            if gtt.symbol != symbol or gtt.status != "ACTIVE":
                continue

            if gtt.check_trigger(current_price):
                gtt.status = "TRIGGERED"
                gtt.triggered_at = now_ist().isoformat()
                triggered.append(gtt)

                logger.info(f"🔔 GTT TRIGGERED: {gtt.id} | {gtt.side} {gtt.quantity} {symbol} "
                            f"@ ₹{current_price:,.2f} (trigger was ₹{gtt.trigger_price:,.2f})")

                # Fire order callback
                if self._order_callback:
                    self._order_callback({
                        "symbol": gtt.symbol,
                        "side": gtt.side,
                        "quantity": gtt.quantity,
                        "price": gtt.limit_price,
                        "order_type": "LIMIT",
                        "source": "GTT",
                        "gtt_id": gtt.id,
                    })

                self.triggered_history.append(gtt.to_dict())

                # Cancel OCO partner
                partner_id = self.oco_pairs.get(gtt_id)
                if partner_id:
                    self.cancel_gtt(partner_id)
                    logger.info(f"🔗 OCO partner cancelled: {partner_id}")

    def get_active_orders(self, symbol: str = None) -> List[Dict]:
        """Get all active GTT orders, optionally filtered by symbol."""
        active = [
            gtt.to_dict()
            for gtt in self.gtt_orders.values()
            if gtt.status == "ACTIVE" and (symbol is None or gtt.symbol == symbol)
        ]
        return active

    def get_all_orders(self) -> List[Dict]:
        """Get all GTT orders (active + triggered + cancelled)."""
        return [gtt.to_dict() for gtt in self.gtt_orders.values()]

"""
Position sizing with F&O lot-size awareness and product type rules.
Reference: SYSTEM_ARCHITECTURE.md §3.6, MISSING_REQUIREMENTS §4
"""

import logging
import yaml
import os
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calculates safe position sizes based on risk parameters.
    Supports:
    - Fixed percentage risk model
    - F&O lot-size enforcement
    - Product type margin rules (MIS/CNC/NRML)
    - Max daily loss tracking
    - Sector concentration limits
    """

    def __init__(
        self,
        total_capital: float,
        max_risk_per_trade: float = 0.01,
        config_path: str = "config/risk_limits.yaml",
    ):
        """
        Args:
            total_capital: Account equity in INR
            max_risk_per_trade: Risk per trade as fraction (0.01 = 1%)
            config_path: Path to risk limits config
        """
        self.capital = total_capital
        self.risk_per_trade = max_risk_per_trade
        self.daily_realized_pnl: float = 0.0

        # Load config
        self.config = self._load_config(config_path)
        self.position_limits = self.config.get("position_limits", {})
        self.product_config = self.config.get("product_types", {})
        self.fno_config = self.config.get("fno", {})
        self.lot_sizes: Dict[str, int] = self.fno_config.get("lot_sizes", {})

    def _load_config(self, path: str) -> Dict:
        if os.path.exists(path):
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    # ─── Core Position Sizing ────────────────────────────────────────

    def calculate_quantity(
        self,
        entry_price: float,
        stop_loss: float,
        lot_size: int = 1,
    ) -> int:
        """
        Calculate quantity based on risk amount and stop distance.
        Quantity = (Total Capital × Risk%) / |Entry - StopLoss|

        For F&O: rounds DOWN to nearest lot size.
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0

        risk_amount = self.capital * self.risk_per_trade
        stop_distance = abs(entry_price - stop_loss)

        if stop_distance == 0:
            logger.warning("⚠️ Stop-loss distance is zero, cannot calculate size")
            return 0

        raw_qty = risk_amount / stop_distance

        # Round to lot size
        if lot_size > 1:
            qty = int(raw_qty // lot_size) * lot_size
        else:
            qty = int(raw_qty)

        # Enforce max order value
        max_value = self.position_limits.get("max_order_value", 500000)
        max_qty_by_value = int(max_value / entry_price)
        qty = min(qty, max_qty_by_value)

        # Enforce max position percentage
        max_pct = self.position_limits.get("max_position_pct", 0.10)
        max_qty_by_pct = int((self.capital * max_pct) / entry_price)
        qty = min(qty, max_qty_by_pct)

        return max(qty, 0)

    def calculate_quantity_fixed_value(
        self,
        entry_price: float,
        allocation: float,
        lot_size: int = 1,
    ) -> int:
        """
        Calculate quantity based on fixed allocation value.
        """
        if entry_price <= 0 or allocation <= 0:
            return 0

        raw_qty = allocation / entry_price

        if lot_size > 1:
            return int(raw_qty // lot_size) * lot_size
        return int(raw_qty)

    # ─── F&O Lot Size ────────────────────────────────────────────────

    def get_lot_size(self, symbol: str) -> int:
        """Get F&O lot size for a symbol."""
        return self.lot_sizes.get(symbol, 1)

    def round_to_lot(self, quantity: int, lot_size: int) -> int:
        """Round quantity down to nearest lot size multiple."""
        if lot_size <= 1:
            return quantity
        return (quantity // lot_size) * lot_size

    def check_freeze_quantity(self, symbol: str, quantity: int) -> Tuple[bool, str]:
        """Check if quantity exceeds freeze limit (max lots per order)."""
        lot_size = self.get_lot_size(symbol)
        max_lots = self.fno_config.get("max_lots_per_order", 36)
        max_qty = max_lots * lot_size

        if quantity > max_qty:
            return False, f"Quantity {quantity} exceeds freeze limit {max_qty} ({max_lots} lots × {lot_size})"
        return True, ""

    # ─── Product Type Margin ─────────────────────────────────────────

    def get_required_margin(
        self,
        quantity: int,
        price: float,
        product_type: str = "INTRADAY",
    ) -> float:
        """Calculate required margin based on product type."""
        gross_value = quantity * price
        product = self.product_config.get(product_type, {})
        margin_pct = product.get("margin_pct", 1.0)
        return gross_value * margin_pct

    def can_afford(
        self,
        quantity: int,
        price: float,
        product_type: str = "INTRADAY",
    ) -> Tuple[bool, float]:
        """
        Check if account can afford the position.
        Returns (can_afford, required_margin).
        """
        required = self.get_required_margin(quantity, price, product_type)
        available = self.capital + self.daily_realized_pnl
        return available >= required, required

    # ─── Daily Loss Tracking ─────────────────────────────────────────

    def record_pnl(self, pnl: float):
        """Record realized P&L for daily loss tracking."""
        self.daily_realized_pnl += pnl

    def is_daily_loss_exceeded(self) -> bool:
        """Check if daily loss limit is exceeded."""
        max_loss_pct = self.position_limits.get("max_daily_loss_pct", 0.03)
        max_loss = self.capital * max_loss_pct
        return self.daily_realized_pnl <= -max_loss

    def reset_daily(self, new_capital: float = None):
        """Reset daily tracking (call at start of each trading day)."""
        self.daily_realized_pnl = 0.0
        if new_capital:
            self.capital = new_capital

    # ─── Validation ──────────────────────────────────────────────────

    def validate_order(
        self,
        quantity: int,
        price: float,
        product_type: str = "INTRADAY",
    ) -> Tuple[bool, Optional[str]]:
        """
        Full validation: affordability, daily loss, position limits.
        Returns (is_valid, error_message).
        """
        # Check daily loss
        if self.is_daily_loss_exceeded():
            return False, "Daily loss limit exceeded — trading halted"

        # Check max order value
        max_value = self.position_limits.get("max_order_value", 500000)
        order_value = quantity * price
        if order_value > max_value:
            return False, f"Order value ₹{order_value:,.0f} exceeds limit ₹{max_value:,.0f}"

        # Check affordability
        can, required = self.can_afford(quantity, price, product_type)
        if not can:
            return False, f"Insufficient margin: required ₹{required:,.0f}"

        return True, None

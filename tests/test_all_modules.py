"""
Tests for utils, risk, compliance, manual, observability, strategies, and engine modules.
Run with: venv\\Scripts\\python -m pytest tests/test_all_modules.py -v
"""

import sys
import os
import asyncio
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, date, time, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════════════
# 1. Utils — Constants
# ═══════════════════════════════════════════════════════════════════════


class TestConstants:
    """Tests for src.utils.constants"""

    def test_exchange_values(self):
        from src.utils.constants import Exchange
        assert Exchange.NSE == "NSE"
        assert Exchange.NFO == "NFO"
        assert Exchange.BSE == "BSE"

    def test_order_types(self):
        from src.utils.constants import OrderType
        assert OrderType.MARKET == "MARKET"
        assert OrderType.LIMIT == "LIMIT"
        assert OrderType.STOPLOSS_LIMIT == "STOPLOSS_LIMIT"

    def test_transaction_types(self):
        from src.utils.constants import TransactionType
        assert TransactionType.BUY == "BUY"
        assert TransactionType.SELL == "SELL"

    def test_intervals(self):
        from src.utils.constants import Interval
        assert Interval.ONE_MINUTE == "ONE_MINUTE"
        assert Interval.FIVE_MINUTE == "FIVE_MINUTE"
        assert Interval.ONE_DAY == "ONE_DAY"

    def test_common_tokens_present(self):
        from src.utils.constants import COMMON_TOKENS
        assert "SBIN" in COMMON_TOKENS
        assert "RELIANCE" in COMMON_TOKENS
        assert "NIFTY_50" in COMMON_TOKENS

    def test_tax_rates_values(self):
        from src.utils.constants import TaxRates
        assert 0 < TaxRates.STT_DELIVERY_BUY < 0.01
        assert TaxRates.GST == 0.18

    def test_trading_days_constant(self):
        from src.utils.constants import TRADING_DAYS_PER_YEAR
        assert TRADING_DAYS_PER_YEAR == 252


# ═══════════════════════════════════════════════════════════════════════
# 2. Utils — Time Utilities
# ═══════════════════════════════════════════════════════════════════════


class TestTimeUtils:
    """Tests for src.utils.time_utils"""

    def test_now_ist_returns_datetime(self):
        from src.utils.time_utils import now_ist
        dt = now_ist()
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None

    def test_is_trading_day_weekend(self):
        from src.utils.time_utils import is_trading_day
        # A Saturday
        assert is_trading_day(date(2025, 2, 15)) is False
        # A Sunday
        assert is_trading_day(date(2025, 2, 16)) is False

    def test_is_trading_day_holiday(self):
        from src.utils.time_utils import is_trading_day, NSE_HOLIDAYS
        # Republic Day 2025 (a known holiday)
        assert is_trading_day(date(2025, 1, 26)) is False

    def test_is_trading_day_weekday(self):
        from src.utils.time_utils import is_trading_day
        # Monday 2025-02-17
        assert is_trading_day(date(2025, 2, 17)) is True

    def test_get_market_session_regular(self):
        from src.utils.time_utils import get_market_session, IST
        # 10:00 AM IST on a weekday
        dt = datetime(2025, 2, 17, 10, 0, tzinfo=IST)
        assert get_market_session(dt) == "REGULAR"

    def test_get_market_session_preopen(self):
        from src.utils.time_utils import get_market_session, IST
        dt = datetime(2025, 2, 17, 9, 5, tzinfo=IST)
        assert get_market_session(dt) == "PRE_OPEN"

    def test_get_market_session_closed(self):
        from src.utils.time_utils import get_market_session, IST
        # 7 AM — before market
        dt = datetime(2025, 2, 17, 7, 0, tzinfo=IST)
        assert get_market_session(dt) == "CLOSED"

    def test_is_market_open(self):
        from src.utils.time_utils import is_market_open, IST
        dt = datetime(2025, 2, 17, 10, 0, tzinfo=IST)
        assert is_market_open(dt) is True

        dt_closed = datetime(2025, 2, 17, 16, 0, tzinfo=IST)
        assert is_market_open(dt_closed) is False

    def test_to_ist(self):
        from src.utils.time_utils import to_ist, IST
        naive_dt = datetime(2025, 1, 1, 12, 0)
        result = to_ist(naive_dt)
        assert result.tzinfo == IST

    def test_get_previous_trading_day(self):
        from src.utils.time_utils import get_previous_trading_day
        # Monday → previous trading day is Friday
        prev = get_previous_trading_day(date(2025, 2, 17))
        assert prev == date(2025, 2, 14)

    def test_get_next_trading_day(self):
        from src.utils.time_utils import get_next_trading_day
        # Friday → next trading day is Monday
        nxt = get_next_trading_day(date(2025, 2, 14))
        assert nxt == date(2025, 2, 17)

    def test_should_square_off_mis(self):
        from src.utils.time_utils import should_square_off_mis, IST
        dt_early = datetime(2025, 2, 17, 14, 0, tzinfo=IST)
        assert should_square_off_mis(dt_early) is False

        dt_late = datetime(2025, 2, 17, 15, 20, tzinfo=IST)
        assert should_square_off_mis(dt_late) is True


# ═══════════════════════════════════════════════════════════════════════
# 3. Utils — Validators
# ═══════════════════════════════════════════════════════════════════════


class TestValidators:
    """Tests for src.utils.validators"""

    def test_validate_order_valid(self):
        from src.utils.validators import validate_order_params
        params = {
            "tradingsymbol": "SBIN",
            "symboltoken": "3045",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "qty": 10,
            "ordertype": "MARKET",
        }
        is_valid, err = validate_order_params(params)
        assert is_valid is True
        assert err is None

    def test_validate_order_missing_field(self):
        from src.utils.validators import validate_order_params
        params = {"tradingsymbol": "SBIN", "symboltoken": "3045"}  # Missing required fields
        is_valid, err = validate_order_params(params)
        assert is_valid is False
        assert "Missing required field" in err

    def test_validate_order_invalid_exchange(self):
        from src.utils.validators import validate_order_params
        params = {
            "tradingsymbol": "SBIN", "symboltoken": "3045",
            "exchange": "INVALID", "transaction_type": "BUY",
            "qty": 10, "ordertype": "MARKET",
        }
        is_valid, err = validate_order_params(params)
        assert is_valid is False
        assert "Invalid exchange" in err

    def test_validate_order_negative_quantity(self):
        from src.utils.validators import validate_order_params
        params = {
            "tradingsymbol": "SBIN", "symboltoken": "3045",
            "exchange": "NSE", "transaction_type": "BUY",
            "qty": -5, "ordertype": "MARKET",
        }
        is_valid, err = validate_order_params(params)
        assert is_valid is False
        assert "positive" in err

    def test_validate_order_limit_without_price(self):
        from src.utils.validators import validate_order_params
        params = {
            "tradingsymbol": "SBIN", "symboltoken": "3045",
            "exchange": "NSE", "transaction_type": "BUY",
            "qty": 10, "ordertype": "LIMIT", "price": 0,
        }
        is_valid, err = validate_order_params(params)
        assert is_valid is False
        assert "Price must be positive" in err

    def test_validate_quantity_lot_size(self):
        from src.utils.validators import validate_quantity_lot_size
        ok, err = validate_quantity_lot_size(50, lot_size=25)
        assert ok is True

        ok, err = validate_quantity_lot_size(30, lot_size=25)
        assert ok is False
        assert "multiple" in err

    def test_validate_price_tick(self):
        from src.utils.validators import validate_price_tick
        assert validate_price_tick(100.03) == 100.05
        assert validate_price_tick(100.07) == 100.05
        assert validate_price_tick(100.10) == 100.10
        assert validate_price_tick(0) == 0.0

    def test_validate_symbol_token(self):
        from src.utils.validators import validate_symbol_token
        ok, err = validate_symbol_token("3045")
        assert ok is True

        ok, err = validate_symbol_token("abc")
        assert ok is False

        ok, err = validate_symbol_token("")
        assert ok is False

    def test_validate_position_value(self):
        from src.utils.validators import validate_position_value
        ok, err = validate_position_value(10, 100.0, max_position_value=5000)
        assert ok is True  # 10 * 100 = 1000 < 5000

        ok, err = validate_position_value(100, 100.0, max_position_value=5000)
        assert ok is False  # 100 * 100 = 10000 > 5000


# ═══════════════════════════════════════════════════════════════════════
# 4. Risk — Position Sizer
# ═══════════════════════════════════════════════════════════════════════


class TestPositionSizer:
    """Tests for src.risk.position_sizer"""

    def _make_sizer(self, capital=100_000):
        from src.risk.position_sizer import PositionSizer
        return PositionSizer(
            total_capital=capital,
            max_risk_per_trade=0.01,
            config_path="nonexistent.yaml",  # Forces empty config
        )

    def test_calculate_quantity_basic(self):
        sizer = self._make_sizer(100_000)
        # Risk = 1% = ₹1000. Entry=100, SL=95 → distance=5 → qty=200
        # But may be limited by max_position_pct(10%) → 10000/100=100
        qty = sizer.calculate_quantity(100.0, 95.0)
        assert qty > 0
        assert isinstance(qty, int)

    def test_calculate_quantity_zero_stop(self):
        sizer = self._make_sizer()
        qty = sizer.calculate_quantity(100.0, 100.0)  # Zero SL distance
        assert qty == 0

    def test_calculate_quantity_invalid_price(self):
        sizer = self._make_sizer()
        assert sizer.calculate_quantity(0, 95.0) == 0
        assert sizer.calculate_quantity(100.0, 0) == 0

    def test_calculate_quantity_with_lot_size(self):
        sizer = self._make_sizer(500_000)
        qty = sizer.calculate_quantity(100.0, 95.0, lot_size=25)
        assert qty % 25 == 0  # Must be a multiple of lot size

    def test_calculate_quantity_fixed_value(self):
        sizer = self._make_sizer()
        qty = sizer.calculate_quantity_fixed_value(100.0, 10_000)
        assert qty == 100

    def test_round_to_lot(self):
        sizer = self._make_sizer()
        assert sizer.round_to_lot(73, 25) == 50
        assert sizer.round_to_lot(100, 25) == 100
        assert sizer.round_to_lot(5, 1) == 5

    def test_get_required_margin_defaults(self):
        sizer = self._make_sizer()
        # Without config, margin_pct defaults to 1.0
        margin = sizer.get_required_margin(10, 500.0, "INTRADAY")
        assert margin == 5000.0  # 10 * 500 * 1.0

    def test_can_afford(self):
        sizer = self._make_sizer(50_000)
        can, req = sizer.can_afford(10, 100.0, "INTRADAY")
        assert can is True  # 1000 << 50000

        can, req = sizer.can_afford(1000, 100.0, "INTRADAY")
        assert can is False  # 100000 > 50000

    def test_daily_loss_tracking(self):
        sizer = self._make_sizer(100_000)
        assert sizer.is_daily_loss_exceeded() is False

        # Record a big loss (3% of 100k = 3000)
        sizer.record_pnl(-3100)
        assert sizer.is_daily_loss_exceeded() is True

    def test_reset_daily(self):
        sizer = self._make_sizer()
        sizer.record_pnl(-5000)
        sizer.reset_daily()
        assert sizer.daily_realized_pnl == 0.0

    def test_validate_order_success(self):
        sizer = self._make_sizer(100_000)
        ok, err = sizer.validate_order(10, 100.0, "INTRADAY")
        assert ok is True
        assert err is None

    def test_validate_order_daily_loss_exceeded(self):
        sizer = self._make_sizer(100_000)
        sizer.record_pnl(-10_000)  # 10% loss, exceeds 3% default
        ok, err = sizer.validate_order(1, 100.0, "INTRADAY")
        assert ok is False
        assert "Daily loss" in err


# ═══════════════════════════════════════════════════════════════════════
# 5. Risk — Circuit Breaker Manager
# ═══════════════════════════════════════════════════════════════════════


class TestCircuitBreakerManager:
    """Tests for src.risk.circuit_breaker_manager"""

    def test_normal_status(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        result = cb.check_market_wide_circuit_breaker("NIFTY_50", 18000, 18500)
        # 500/18500 = 2.7% decline, no circuit
        assert result["status"] == "NORMAL"

    def test_mwcb_level1(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        # 11% decline
        result = cb.check_market_wide_circuit_breaker("NIFTY_50", 16000, 18000)
        assert result["status"] == "HALTED"
        assert result["level"] == "LEVEL_1"

    def test_mwcb_level3(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        # 22% decline
        result = cb.check_market_wide_circuit_breaker("NIFTY_50", 14000, 18000)
        assert result["status"] == "HALTED"
        assert result["level"] == "LEVEL_3"
        assert result["halt_minutes"] == -1  # Close for day

    def test_stock_upper_circuit(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        cb.update_stock_limit("TESTSTOCK", 0.10)
        result = cb.check_stock_circuit_limit("TESTSTOCK", 115.0, 100.0)
        assert result["status"] == "UPPER_CIRCUIT"
        assert "TESTSTOCK" in cb.halted_stocks

    def test_stock_lower_circuit(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        cb.update_stock_limit("TESTSTOCK", 0.10)
        result = cb.check_stock_circuit_limit("TESTSTOCK", 85.0, 100.0)
        assert result["status"] == "LOWER_CIRCUIT"

    def test_stock_normal_movement(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        cb.update_stock_limit("TESTSTOCK", 0.10)
        result = cb.check_stock_circuit_limit("TESTSTOCK", 105.0, 100.0)
        assert result["status"] == "NORMAL"

    def test_is_execution_allowed(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        assert cb.is_execution_allowed("SBIN") is True

        cb.halted_stocks.add("SBIN")
        assert cb.is_execution_allowed("SBIN") is False

    def test_is_execution_blocked_during_mwcb(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        cb.mwcb_status = "HALTED"
        assert cb.is_execution_allowed("SBIN") is False

    def test_get_status(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        status = cb.get_status()
        assert "mwcb_status" in status
        assert "halted_stocks" in status
        assert status["mwcb_status"] == "NORMAL"

    def test_bulk_update_limits(self):
        from src.risk.circuit_breaker_manager import CircuitBreakerManager
        cb = CircuitBreakerManager()
        cb.bulk_update_limits({"A": 0.05, "B": 0.10})
        assert cb.stock_limits["A"] == 0.05
        assert cb.stock_limits["B"] == 0.10


# ═══════════════════════════════════════════════════════════════════════
# 6. Compliance — SEBI
# ═══════════════════════════════════════════════════════════════════════


class TestSEBICompliance:
    """Tests for src.compliance.sebi_compliance"""

    def test_register_algorithm(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        result = mgr.register_algorithm("TestStrategy", {"type": "EMA"})
        assert result is True
        assert mgr.registration_status == "REGISTERED"
        assert mgr.algo_id is not None

    def test_register_invalid(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        result = mgr.register_algorithm("", {})
        assert result is False
        assert mgr.registration_status == "UNREGISTERED"

    def test_validate_order_tags(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        mgr.register_algorithm("TestStrategy", {"type": "EMA"})

        order = {"symbol": "SBIN", "qty": 10}
        tagged = mgr.validate_order(order)
        assert "algo_id" in tagged
        assert "algo_tag" in tagged
        assert tagged["algo_tag"] == "ALGO"

    def test_validate_order_unregistered(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        with pytest.raises(RuntimeError, match="not registered"):
            mgr.validate_order({"symbol": "X"})

    def test_rate_limit_enforcement(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        mgr.register_algorithm("TestStrategy", {"type": "EMA"})

        # Send ops_threshold + 1 orders in the same second
        with pytest.raises(RuntimeError, match="OPS threshold"):
            for _ in range(mgr.ops_threshold + 2):
                mgr.validate_order({"symbol": "X"})

    def test_audit_trail(self):
        from src.compliance.sebi_compliance import SEBIAlgoComplianceManager
        mgr = SEBIAlgoComplianceManager("BROKER001")
        # Should not raise
        mgr.log_audit_trail("ORDER_PLACED", {"symbol": "SBIN", "qty": 10})


# ═══════════════════════════════════════════════════════════════════════
# 7. Manual — GTT Order Manager
# ═══════════════════════════════════════════════════════════════════════


class TestGTTOrderManager:
    """Tests for src.manual.order_manager"""

    def test_place_gtt(self):
        from src.manual.order_manager import AdvancedOrderManager
        mgr = AdvancedOrderManager()
        gtt_id = mgr.place_gtt("SBIN", 500.0, 500.0, 10, "BUY", "GTE")
        assert gtt_id.startswith("GTT-")
        assert len(mgr.get_active_orders()) == 1

    def test_gtt_trigger(self):
        from src.manual.order_manager import AdvancedOrderManager
        fired = []
        mgr = AdvancedOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_gtt("SBIN", 500.0, 500.0, 10, "BUY", "GTE")
        mgr.check_triggers("SBIN", 510.0)  # Price >= trigger
        assert len(fired) == 1
        assert fired[0]["symbol"] == "SBIN"
        assert fired[0]["source"] == "GTT"

    def test_gtt_no_trigger(self):
        from src.manual.order_manager import AdvancedOrderManager
        fired = []
        mgr = AdvancedOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_gtt("SBIN", 500.0, 500.0, 10, "BUY", "GTE")
        mgr.check_triggers("SBIN", 490.0)  # Price < trigger
        assert len(fired) == 0

    def test_cancel_gtt(self):
        from src.manual.order_manager import AdvancedOrderManager
        mgr = AdvancedOrderManager()
        gtt_id = mgr.place_gtt("SBIN", 500.0, 500.0, 10)
        result = mgr.cancel_gtt(gtt_id)
        assert result is True
        assert len(mgr.get_active_orders()) == 0

    def test_place_oco(self):
        from src.manual.order_manager import AdvancedOrderManager
        mgr = AdvancedOrderManager()
        target_id, sl_id = mgr.place_oco("SBIN", 520.0, 480.0, 10)
        assert len(mgr.get_active_orders()) == 2

        # Trigger target — should cancel SL
        mgr.check_triggers("SBIN", 525.0)
        active = mgr.get_active_orders()
        assert len(active) == 0  # Both resolved: one triggered, one cancelled

    def test_lte_condition(self):
        from src.manual.order_manager import AdvancedOrderManager
        fired = []
        mgr = AdvancedOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_gtt("SBIN", 480.0, 480.0, 10, "SELL", "LTE")
        mgr.check_triggers("SBIN", 470.0)
        assert len(fired) == 1
        assert fired[0]["side"] == "SELL"


# ═══════════════════════════════════════════════════════════════════════
# 8. Manual — Bracket Orders
# ═══════════════════════════════════════════════════════════════════════


class TestBracketOrders:
    """Tests for src.manual.bracket_orders"""

    def test_place_bracket_order(self):
        from src.manual.bracket_orders import BracketOrderManager
        mgr = BracketOrderManager()
        bo_id = mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)
        assert bo_id.startswith("BO-")
        active = mgr.get_active_orders()
        assert len(active) == 1

    def test_bracket_entry_fill(self):
        from src.manual.bracket_orders import BracketOrderManager
        fired = []
        mgr = BracketOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)

        # Price touches entry
        mgr.check_prices("SBIN", 500.0)
        # Entry should be filled, order_callback should fire
        assert len(fired) >= 1

    def test_bracket_target_hit(self):
        from src.manual.bracket_orders import BracketOrderManager
        fired = []
        mgr = BracketOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)

        mgr.check_prices("SBIN", 500.0)  # Entry fill
        mgr.check_prices("SBIN", 520.0)  # Target hit

        completed = mgr.get_completed_orders()
        assert len(completed) >= 1

    def test_bracket_stoploss_hit(self):
        from src.manual.bracket_orders import BracketOrderManager
        fired = []
        mgr = BracketOrderManager()
        mgr.set_order_callback(lambda o: fired.append(o))

        mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)

        mgr.check_prices("SBIN", 500.0)  # Entry fill
        mgr.check_prices("SBIN", 485.0)  # SL hit

        completed = mgr.get_completed_orders()
        assert len(completed) >= 1

    def test_cancel_pending(self):
        from src.manual.bracket_orders import BracketOrderManager
        mgr = BracketOrderManager()
        bo_id = mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)
        result = mgr.cancel(bo_id)
        assert result is True
        assert len(mgr.get_active_orders()) == 0

    def test_modify_sl(self):
        from src.manual.bracket_orders import BracketOrderManager
        mgr = BracketOrderManager()
        bo_id = mgr.place_bracket_order("SBIN", "BUY", 10, 500.0, 490.0, 520.0)
        mgr.check_prices("SBIN", 500.0)  # Fill entry
        result = mgr.modify_sl(bo_id, 495.0)
        assert result is True


# ═══════════════════════════════════════════════════════════════════════
# 9. Manual — Paper Portfolio
# ═══════════════════════════════════════════════════════════════════════


class TestPaperPortfolio:
    """Tests for src.manual.paper_portfolio"""

    def test_buy_order(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        result = pf.execute_order("SBIN", "BUY", 10, 500.0)
        assert result["status"] == "COMPLETE"
        assert pf.cash == 100_000 - (10 * 500)
        assert "SBIN" in pf.holdings
        assert pf.holdings["SBIN"]["qty"] == 10

    def test_sell_for_pnl(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        pf.execute_order("SBIN", "SELL", 10, 510.0)
        assert pf.realized_pnl == 100.0  # 10 * (510 - 500)
        assert "SBIN" not in pf.holdings

    def test_insufficient_funds(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=1_000)
        result = pf.execute_order("RELIANCE", "BUY", 100, 2500.0)  # 250k > 1k
        assert result["status"] == "REJECTED"
        assert result["reason"] == "INSUFFICIENT_FUNDS"

    def test_insufficient_quantity(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 5, 500.0)
        result = pf.execute_order("SBIN", "SELL", 10, 510.0)
        assert result["status"] == "REJECTED"

    def test_portfolio_value(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        val = pf.get_portfolio_value({"SBIN": 520.0})
        expected = 95_000 + 10 * 520  # cash + holdings
        assert val == expected

    def test_unrealized_pnl(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        pnl = pf.get_unrealized_pnl({"SBIN": 520.0})
        assert pnl == 200.0  # 10 * (520 - 500)

    def test_summary(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        summary = pf.get_summary({"SBIN": 500.0})
        assert summary["holdings_count"] == 1
        assert summary["trade_count"] == 1

    def test_square_off_all(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        pf.execute_order("INFY", "BUY", 5, 1500.0)

        results = pf.square_off_all({"SBIN": 510.0, "INFY": 1490.0})
        assert len(results) == 2
        assert len(pf.holdings) == 0

    def test_reset_daily(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio()
        pf.daily_realized_pnl = 500.0
        pf.reset_daily()
        assert pf.daily_realized_pnl == 0.0

    def test_order_history(self):
        from src.manual.paper_portfolio import PaperPortfolio
        pf = PaperPortfolio(initial_capital=100_000)
        pf.execute_order("SBIN", "BUY", 10, 500.0)
        pf.execute_order("SBIN", "SELL", 10, 510.0)
        history = pf.get_order_history()
        assert len(history) == 2


# ═══════════════════════════════════════════════════════════════════════
# 10. Observability — Health Check
# ═══════════════════════════════════════════════════════════════════════


class TestHealthChecker:
    """Tests for src.observability.health_check"""

    def test_default_status(self):
        from src.observability.health_check import HealthChecker
        hc = HealthChecker()
        assert hc.is_healthy() is True

    def test_update_component(self):
        from src.observability.health_check import HealthChecker
        hc = HealthChecker()
        hc.update_component("broker_auth", "healthy")
        health = hc.get_health()
        assert health["components"]["broker_auth"]["status"] == "healthy"

    def test_unhealthy_component(self):
        from src.observability.health_check import HealthChecker
        hc = HealthChecker()
        hc.update_component("broker_auth", "unhealthy")
        assert hc.is_healthy() is False
        health = hc.get_health()
        assert health["status"] == "unhealthy"

    def test_degraded_component(self):
        from src.observability.health_check import HealthChecker
        hc = HealthChecker()
        hc.update_component("data_bridge", "degraded", {"queue_size": 5000})
        health = hc.get_health()
        assert health["status"] == "degraded"

    def test_system_metrics(self):
        from src.observability.health_check import HealthChecker
        hc = HealthChecker()
        health = hc.get_health()
        assert "system" in health
        assert "memory_mb" in health["system"]
        assert "cpu_percent" in health["system"]
        assert "uptime_seconds" in health


# ═══════════════════════════════════════════════════════════════════════
# 11. Strategies — Indicators
# ═══════════════════════════════════════════════════════════════════════


class TestIndicators:
    """Tests for src.strategies.indicators"""

    def _sample_df(self, n=100):
        np.random.seed(42)
        prices = 500 + np.cumsum(np.random.randn(n) * 2)
        return pd.DataFrame({
            "open": prices + np.random.randn(n),
            "high": prices + abs(np.random.randn(n) * 2),
            "low": prices - abs(np.random.randn(n) * 2),
            "close": prices,
            "volume": np.random.randint(1000, 50000, n),
        })

    def test_sma(self):
        from src.strategies.indicators import sma
        df = self._sample_df()
        result = sma(df["close"], 10)
        assert len(result) == len(df)
        assert pd.isna(result.iloc[0])  # First values are NaN
        assert not pd.isna(result.iloc[20])

    def test_ema(self):
        from src.strategies.indicators import ema
        df = self._sample_df()
        result = ema(df["close"], 10)
        assert len(result) == len(df)

    def test_rsi(self):
        from src.strategies.indicators import rsi
        df = self._sample_df()
        result = rsi(df["close"], 14)
        valid = result.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_macd(self):
        from src.strategies.indicators import macd
        df = self._sample_df()
        macd_line, signal, histogram = macd(df["close"])
        assert len(macd_line) == len(df)
        assert len(signal) == len(df)
        assert len(histogram) == len(df)

    def test_bollinger_bands(self):
        from src.strategies.indicators import bollinger_bands
        df = self._sample_df()
        upper, middle, lower = bollinger_bands(df["close"], 20)
        valid_idx = ~pd.isna(upper)
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()

    def test_atr(self):
        from src.strategies.indicators import atr
        df = self._sample_df()
        result = atr(df, 14)
        valid = result.dropna()
        assert (valid > 0).all()

    def test_vwap(self):
        from src.strategies.indicators import vwap
        df = self._sample_df()
        result = vwap(df)
        assert len(result) == len(df)
        assert (result > 0).all()

    def test_stochastic(self):
        from src.strategies.indicators import stochastic
        df = self._sample_df()
        k, d = stochastic(df, 14, 3)
        valid_k = k.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()

    def test_adx(self):
        from src.strategies.indicators import adx
        df = self._sample_df()
        result = adx(df, 14)
        # adx returns a DataFrame with ADX column(s)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_supertrend(self):
        from src.strategies.indicators import supertrend
        df = self._sample_df()
        result = supertrend(df, 10, 3.0)
        # supertrend returns a DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_obv(self):
        from src.strategies.indicators import obv
        df = self._sample_df()
        result = obv(df)
        assert len(result) == len(df)


# ═══════════════════════════════════════════════════════════════════════
# 12. Strategies — Base Strategy
# ═══════════════════════════════════════════════════════════════════════


class TestBaseStrategy:
    """Tests for src.strategies.base_strategy"""

    def test_instantiation(self):
        from src.strategies.base_strategy import BaseStrategy

        class TestStrat(BaseStrategy):
            def on_bar(self, bar):
                super().on_bar(bar)

        s = TestStrat({"name": "test"})
        assert s.name == "test"
        assert s.bar_count == 0

    def test_on_bar_increments_count(self):
        from src.strategies.base_strategy import BaseStrategy

        class TestStrat(BaseStrategy):
            def on_bar(self, bar):
                super().on_bar(bar)

        s = TestStrat({"name": "test"})
        s.on_bar({"close": 100, "open": 100, "high": 101, "low": 99, "volume": 1000, "timestamp": "2025-01-01"})
        assert s.bar_count == 1

    def test_generate_signal(self):
        from src.strategies.base_strategy import BaseStrategy

        class TestStrat(BaseStrategy):
            def on_bar(self, bar):
                super().on_bar(bar)

        s = TestStrat({"name": "test"})
        s.generate_signal("BUY", 100.0, "test reason")
        assert len(s.signals) == 1
        assert s.signals[0]["type"] == "BUY"

    def test_update_position(self):
        from src.strategies.base_strategy import BaseStrategy

        class TestStrat(BaseStrategy):
            def on_bar(self, bar):
                super().on_bar(bar)

        s = TestStrat({"name": "test"})
        s.update_position("BUY", 10, 500.0)
        assert s.position == 10
        assert s.entry_price == 500.0

    def test_on_start_on_stop(self):
        from src.strategies.base_strategy import BaseStrategy

        class TestStrat(BaseStrategy):
            started = False
            stopped = False
            def on_start(self):
                super().on_start()
                self.started = True
            def on_stop(self):
                super().on_stop()
                self.stopped = True
            def on_bar(self, bar):
                super().on_bar(bar)

        s = TestStrat({"name": "test"})
        s.on_start()
        assert s.started
        s.on_stop()
        assert s.stopped


# ═══════════════════════════════════════════════════════════════════════
# 13. Strategies — EMA Crossover
# ═══════════════════════════════════════════════════════════════════════


class TestEMACrossoverStrategy:
    """Tests for src.strategies.ema_crossover"""

    def test_initialization(self):
        from src.strategies.ema_crossover import EMACrossoverStrategy
        s = EMACrossoverStrategy({"name": "ema_test", "fast_period": 9, "slow_period": 21, "quantity": 10})
        assert s.name == "ema_test"
        assert s.fast_period == 9

    def test_processes_bars_without_error(self):
        from src.strategies.ema_crossover import EMACrossoverStrategy
        from src.data.data_manager import HistoricalDataManager

        s = EMACrossoverStrategy({"name": "ema_test", "fast_period": 9, "slow_period": 21, "quantity": 10})
        s.on_start()

        data = HistoricalDataManager.create_sample_data(days=5)
        for _, row in data.iterrows():
            bar = {
                "timestamp": str(row["timestamp"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
            s.on_bar(bar)

        assert s.bar_count > 0
        s.on_stop()


# ═══════════════════════════════════════════════════════════════════════
# 14. Observability — Metrics
# ═══════════════════════════════════════════════════════════════════════


class TestMetrics:
    """Tests for src.observability.metrics"""

    def test_init_metrics(self):
        from src.observability.metrics import init_metrics
        # Should not raise
        init_metrics()

    def test_metrics_exist(self):
        from src.observability.metrics import (
            ORDERS_PLACED, ORDERS_REJECTED, TICKS_RECEIVED,
            PORTFOLIO_VALUE, OPEN_POSITIONS, DAILY_PNL,
        )
        # Verify they're valid metric objects
        assert ORDERS_PLACED is not None
        assert PORTFOLIO_VALUE is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

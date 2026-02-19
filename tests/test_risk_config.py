import os
import pytest
import sys
from unittest.mock import MagicMock

# Add project root to sys.path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.risk.position_sizer import PositionSizer

def test_position_sizer_loading_real_config():
    """Verify that PositionSizer loads the actual risk_limits.yaml."""
    config_path = "config/risk_limits.yaml"
    if not os.path.exists(config_path):
        pytest.skip("config/risk_limits.yaml not found")
        
    sizer = PositionSizer(total_capital=1000000, config_path=config_path)
    
    # Check if some values from the YAML are loaded
    # Based on our view of the file:
    # max_position_pct: 0.10
    # max_order_value: 500000
    assert sizer.position_limits.get("max_position_pct") == 0.10
    assert sizer.position_limits.get("max_order_value") == 500000
    
    # Check lot sizes
    assert sizer.get_lot_size("NIFTY") == 25
    assert sizer.get_lot_size("BANKNIFTY") == 15

def test_position_sizer_application_of_limits():
    """Verify that loaded limits are actually applied in calculations."""
    config_path = "config/risk_limits.yaml"
    sizer = PositionSizer(total_capital=100000, config_path=config_path)
    
    # Total Capital = 1 Lakh
    # Max Order Value = 5 Lakh (from config)
    # Max Position Pct = 10% = 10k
    
    # Entry=100, SL=95 -> Risk is 5 per share.
    # Risk per trade = 1% = 1000.
    # Risk-based qty = 1000 / 5 = 200.
    # Position value @ 100 = 200 * 100 = 20k.
    # But Max Position Pct (10%) limits position value to 10k.
    # So qty should be 100.
    
    qty = sizer.calculate_quantity(entry_price=100.0, stop_loss=95.0)
    assert qty == 100 

def test_position_sizer_margin_rules():
    """Verify margin calculations based on product_types in YAML."""
    config_path = "config/risk_limits.yaml"
    sizer = PositionSizer(total_capital=100000, config_path=config_path)
    
    # MIS margin_pct: 0.20
    # CNC margin_pct: 1.0
    
    assert sizer.get_required_margin(10, 100.0, "MIS") == 200.0
    assert sizer.get_required_margin(10, 100.0, "CNC") == 1000.0

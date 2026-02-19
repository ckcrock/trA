import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from decimal import Decimal

# Add project root to sys.path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategies.indicators import rsi, supertrend

# Pure Python logic replication for testing (identical to on_bar in real strategies)
class RSIReviewer:
    def __init__(self, period=14, oversold=30, overbought=70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.prices = []
        self.log = MagicMock()
        
    def on_bar(self, close):
        self.prices.append(float(close))
        if len(self.prices) < self.period + 1:
            return None
        
        series = pd.Series(self.prices)
        current_rsi = rsi(series, self.period).iloc[-1]
        
        if pd.isna(current_rsi): return None
        
        if current_rsi < self.oversold: return "BUY"
        if current_rsi > self.overbought: return "SELL"
        return None

class SupertrendReviewer:
    def __init__(self, period=10, multiplier=3.0):
        self.period = period
        self.multiplier = multiplier
        self.bars = []
        
    def on_bar(self, high, low, close):
        self.bars.append({"high": high, "low": low, "close": close})
        if len(self.bars) < self.period + 1:
            return None
            
        df = pd.DataFrame(self.bars)
        st_df = supertrend(df, self.period, self.multiplier)
        
        current = st_df.iloc[-1]
        previous = st_df.iloc[-2]
        
        if pd.isna(current["supertrend"]) or pd.isna(previous["supertrend"]):
            return None
            
        if current["supertrend_direction"] == 1 and previous["supertrend_direction"] == -1:
            return "BUY"
        if current["supertrend_direction"] == -1 and previous["supertrend_direction"] == 1:
            return "SELL"
        return None

def test_rsi_signal_logic():
    reviewer = RSIReviewer(period=2, oversold=30, overbought=70)
    
    # Needs 3 bars for RSI(2)
    assert reviewer.on_bar(100) is None
    assert reviewer.on_bar(95) is None
    
    # Massive drop for oversold
    signal = reviewer.on_bar(50)
    assert signal == "BUY"
    
    # Massive pump for overbought
    reviewer.on_bar(150)
    signal = reviewer.on_bar(200)
    assert signal == "SELL"

def test_supertrend_signal_logic():
    reviewer = SupertrendReviewer(period=3, multiplier=1.0)
    
    # Establish upward trend
    reviewer.on_bar(100, 99, 100)
    reviewer.on_bar(102, 101, 102)
    reviewer.on_bar(104, 103, 104)
    reviewer.on_bar(106, 105, 106)
    
    # Crash to trigger reversal
    signal = reviewer.on_bar(50, 48, 49)
    assert signal == "SELL"
    
    # Recovery to trigger reversal
    reviewer.on_bar(52, 51, 52)
    reviewer.on_bar(54, 53, 54)
    signal = reviewer.on_bar(120, 110, 115)
    assert signal == "BUY"

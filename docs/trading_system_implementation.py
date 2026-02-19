#!/usr/bin/env python3
"""
COMPLETE TRADING IMPLEMENTATION
Technical Indicators, Strategies & Angel One Integration

Author: Trading System
Date: February 2026
Purpose: Production-ready implementation of all indicators and strategies
"""

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
import talib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: ANGEL ONE SCRIP MASTER MANAGEMENT
# ============================================================================

class AngelScripMaster:
    """
    Download and manage Angel One instrument master
    """
    
    SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    
    def __init__(self, cache_path: str = "data/instruments/"):
        self.cache_path = cache_path
        self.instruments_df = None
        
    def download_scrip_master(self) -> pd.DataFrame:
        """
        Download latest scrip master from Angel One
        
        Returns:
            DataFrame with all instruments
        """
        logger.info("Downloading Angel One scrip master...")
        
        try:
            response = requests.get(self.SCRIP_MASTER_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data)
            
            # Convert expiry to datetime
            df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce')
            
            # Add derived columns
            df['is_equity'] = df['instrumenttype'] == 'EQ'
            df['is_futures'] = df['instrumenttype'].isin(['FUTIDX', 'FUTSTK'])
            df['is_options'] = df['instrumenttype'].isin(['OPTIDX', 'OPTSTK'])
            
            # Save to cache
            filename = f"{self.cache_path}angel_scrip_master_{datetime.now().strftime('%Y%m%d')}.csv"
            df.to_csv(filename, index=False)
            
            logger.info(f"✅ Downloaded {len(df)} instruments")
            logger.info(f"Saved to: {filename}")
            
            self.instruments_df = df
            return df
            
        except Exception as e:
            logger.error(f"❌ Error downloading scrip master: {e}")
            return None
    
    def load_cached_scrip_master(self) -> Optional[pd.DataFrame]:
        """Load most recent cached scrip master"""
        import glob
        import os
        
        pattern = f"{self.cache_path}angel_scrip_master_*.csv"
        files = glob.glob(pattern)
        
        if not files:
            logger.warning("No cached scrip master found. Downloading...")
            return self.download_scrip_master()
        
        # Get most recent file
        latest_file = max(files, key=os.path.getctime)
        logger.info(f"Loading cached scrip master: {latest_file}")
        
        df = pd.read_csv(latest_file)
        df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce')
        self.instruments_df = df
        
        return df
    
    def find_token(self, search_term: str, exchange: str = 'NSE') -> pd.DataFrame:
        """
        Search for instrument token
        
        Args:
            search_term: Symbol to search (e.g., "SBIN", "NIFTY")
            exchange: NSE, BSE, NFO, MCX
        
        Returns:
            DataFrame with matching instruments
        """
        if self.instruments_df is None:
            self.load_cached_scrip_master()
        
        search_term = search_term.upper()
        mask = (
            self.instruments_df['symbol'].str.contains(search_term, na=False) &
            self.instruments_df['exch_seg'].str.contains(exchange, na=False)
        )
        
        results = self.instruments_df[mask]
        return results[['token', 'symbol', 'name', 'exch_seg', 'instrumenttype', 'lotsize', 'expiry']]
    
    def get_nifty50_stocks(self) -> List[Dict]:
        """
        Get top Nifty 50 stocks with tokens
        
        Returns:
            List of dicts with symbol, token, name
        """
        nifty50_symbols = [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
            'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'BAJFINANCE',
            'KOTAKBANK', 'AXISBANK', 'HCLTECH', 'MARUTI', 'ASIANPAINT',
            'WIPRO', 'LT', 'TITAN', 'TATAMOTORS', 'ULTRACEMCO',
            'SUNPHARMA', 'NESTLEIND', 'TECHM', 'TATASTEEL', 'POWERGRID',
            'NTPC', 'ONGC', 'BAJAJFINSV', 'M&M', 'ADANIENT',
            'INDUSINDBK', 'JSWSTEEL', 'HINDALCO', 'GRASIM', 'DRREDDY',
            'COALINDIA', 'EICHERMOT', 'BRITANNIA', 'CIPLA', 'SHREECEM',
            'DIVISLAB', 'HEROMOTOCO', 'SBILIFE', 'TATACONSUM', 'BAJAJ-AUTO',
            'APOLLOHOSP', 'ADANIPORTS', 'BPCL', 'HDFCLIFE', 'UPL'
        ]
        
        stocks = []
        for symbol in nifty50_symbols:
            result = self.find_token(symbol, 'NSE')
            if not result.empty:
                equity = result[result['instrumenttype'] == 'EQ'].iloc[0]
                stocks.append({
                    'symbol': symbol,
                    'token': equity['token'],
                    'name': equity['name'],
                    'lotsize': equity['lotsize']
                })
        
        return stocks
    
    def get_index_tokens(self) -> Dict[str, str]:
        """Get major index tokens"""
        indices = {
            'NIFTY50': '26000',
            'BANKNIFTY': '26009',
            'FINNIFTY': '26037',
            'NIFTYIT': '26017',
            'NIFTYPHARMA': '26023',
            'NIFTYAUTO': '26001',
            'SENSEX': '1',
        }
        return indices
    
    def get_liquid_stocks_for_intraday(self, min_volume: int = 1000000) -> pd.DataFrame:
        """
        Get high-liquidity stocks suitable for intraday
        
        Args:
            min_volume: Minimum average daily volume
        
        Returns:
            DataFrame with liquid stocks
        """
        if self.instruments_df is None:
            self.load_cached_scrip_master()
        
        # Filter for NSE equity stocks only
        liquid_stocks = self.instruments_df[
            (self.instruments_df['exch_seg'] == 'NSE') &
            (self.instruments_df['instrumenttype'] == 'EQ')
        ].copy()
        
        # Get F&O stocks (they are most liquid)
        fo_symbols = self.instruments_df[
            (self.instruments_df['exch_seg'] == 'NFO') &
            (self.instruments_df['instrumenttype'].isin(['FUTSTK', 'OPTSTK']))
        ]['symbol'].str.replace('-EQ', '').unique()
        
        liquid_stocks = liquid_stocks[
            liquid_stocks['symbol'].str.replace('-EQ', '').isin(fo_symbols)
        ]
        
        logger.info(f"Found {len(liquid_stocks)} liquid F&O stocks")
        
        return liquid_stocks[['token', 'symbol', 'name']]


# ============================================================================
# PART 2: TECHNICAL INDICATORS LIBRARY
# ============================================================================

class TechnicalIndicators:
    """
    Complete technical indicators implementation
    """
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Relative Strength Index
        
        Values:
        - 0-30: Oversold
        - 30-70: Neutral
        - 70-100: Overbought
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD - Moving Average Convergence Divergence
        
        Returns:
            (macd_line, signal_line, histogram)
        """
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Bollinger Bands
        
        Returns:
            (upper_band, middle_band, lower_band)
        """
        middle_band = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average True Range - Volatility indicator
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        return atr
    
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Volume Weighted Average Price - CRITICAL for intraday
        """
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap
    
    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Supertrend indicator - Popular in Indian markets
        
        Returns:
            (supertrend_line, direction)
            direction: 1 = uptrend, -1 = downtrend
        """
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        # Calculate basic bands
        hl_avg = (high + low) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)
        
        # Initialize supertrend
        supertrend = pd.Series(index=close.index, dtype=float)
        direction = pd.Series(index=close.index, dtype=int)
        
        supertrend.iloc[0] = lower_band.iloc[0]
        direction.iloc[0] = 1
        
        for i in range(1, len(close)):
            if close.iloc[i] > upper_band.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            elif close.iloc[i] < lower_band.iloc[i-1]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]
                
                if direction.iloc[i] == 1 and supertrend.iloc[i] < supertrend.iloc[i-1]:
                    supertrend.iloc[i] = supertrend.iloc[i-1]
                elif direction.iloc[i] == -1 and supertrend.iloc[i] > supertrend.iloc[i-1]:
                    supertrend.iloc[i] = supertrend.iloc[i-1]
        
        return supertrend, direction
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        Average Directional Index - Trend strength
        
        Values:
        - 0-25: Weak/no trend
        - 25-50: Strong trend
        - 50+: Very strong trend
        """
        return talib.ADX(high.values, low.values, close.values, timeperiod=period)
    
    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Stochastic Oscillator
        
        Returns:
            (k_percent, d_percent)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
    
    @staticmethod
    def pivot_points(previous_high: float, previous_low: float, previous_close: float) -> Dict[str, float]:
        """
        Pivot Points - CRITICAL for Indian intraday trading
        
        Returns:
            Dict with pivot, r1, r2, r3, s1, s2, s3
        """
        pivot = (previous_high + previous_low + previous_close) / 3
        
        r1 = (2 * pivot) - previous_low
        r2 = pivot + (previous_high - previous_low)
        r3 = previous_high + 2 * (pivot - previous_low)
        
        s1 = (2 * pivot) - previous_high
        s2 = pivot - (previous_high - previous_low)
        s3 = previous_low - 2 * (previous_high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """On Balance Volume - Volume indicator"""
        obv = (volume * (~close.diff().le(0) * 2 - 1)).cumsum()
        return obv
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all major indicators on a DataFrame
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with all indicators added
        """
        # Moving averages
        df['sma_20'] = TechnicalIndicators.sma(df['close'], 20)
        df['sma_50'] = TechnicalIndicators.sma(df['close'], 50)
        df['sma_200'] = TechnicalIndicators.sma(df['close'], 200)
        df['ema_9'] = TechnicalIndicators.ema(df['close'], 9)
        df['ema_21'] = TechnicalIndicators.ema(df['close'], 21)
        
        # Momentum indicators
        df['rsi'] = TechnicalIndicators.rsi(df['close'], 14)
        df['macd'], df['macd_signal'], df['macd_hist'] = TechnicalIndicators.macd(df['close'])
        
        # Volatility indicators
        df['upper_bb'], df['middle_bb'], df['lower_bb'] = TechnicalIndicators.bollinger_bands(df['close'])
        df['atr'] = TechnicalIndicators.atr(df['high'], df['low'], df['close'])
        
        # Trend indicators
        df['supertrend'], df['supertrend_dir'] = TechnicalIndicators.supertrend(
            df['high'], df['low'], df['close']
        )
        
        # Volume indicators
        df['vwap'] = TechnicalIndicators.vwap(df['high'], df['low'], df['close'], df['volume'])
        df['obv'] = TechnicalIndicators.obv(df['close'], df['volume'])
        
        # Stochastic
        df['stoch_k'], df['stoch_d'] = TechnicalIndicators.stochastic(
            df['high'], df['low'], df['close']
        )
        
        logger.info("✅ Calculated all technical indicators")
        return df


# ============================================================================
# PART 3: TRADING STRATEGIES
# ============================================================================

class TradingStrategies:
    """
    Pre-built trading strategies
    """
    
    @staticmethod
    def vwap_scalping(df: pd.DataFrame) -> pd.Series:
        """
        VWAP Scalping Strategy - Intraday
        
        Entry:
        - LONG: Price dips to VWAP, RSI < 50, volume spike
        - SHORT: Price rises to VWAP, RSI > 50, volume spike
        
        Returns:
            Series with signals: 1 (BUY), -1 (SELL), 0 (HOLD)
        """
        signals = pd.Series(0, index=df.index)
        
        # Calculate conditions
        price_near_vwap = abs(df['close'] - df['vwap']) / df['vwap'] < 0.002  # Within 0.2%
        volume_spike = df['volume'] > df['volume'].rolling(20).mean() * 1.5
        
        # LONG signals
        long_condition = (
            price_near_vwap &
            (df['rsi'] < 50) &
            volume_spike &
            (df['close'] > df['open'])  # Bullish candle
        )
        
        # SHORT signals
        short_condition = (
            price_near_vwap &
            (df['rsi'] > 50) &
            volume_spike &
            (df['close'] < df['open'])  # Bearish candle
        )
        
        signals[long_condition] = 1
        signals[short_condition] = -1
        
        return signals
    
    @staticmethod
    def ema_crossover(df: pd.DataFrame, fast: int = 9, slow: int = 21) -> pd.Series:
        """
        EMA Crossover Strategy - Intraday/Swing
        
        Entry:
        - LONG: Fast EMA crosses above Slow EMA
        - SHORT: Fast EMA crosses below Slow EMA
        
        Returns:
            Series with signals: 1 (BUY), -1 (SELL), 0 (HOLD)
        """
        signals = pd.Series(0, index=df.index)
        
        ema_fast = TechnicalIndicators.ema(df['close'], fast)
        ema_slow = TechnicalIndicators.ema(df['close'], slow)
        
        # Crossover detection
        cross_above = (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))
        cross_below = (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))
        
        signals[cross_above] = 1
        signals[cross_below] = -1
        
        return signals
    
    @staticmethod
    def opening_range_breakout(df: pd.DataFrame, or_minutes: int = 15) -> pd.Series:
        """
        Opening Range Breakout - Intraday
        
        Method:
        1. Calculate first 15-min high/low
        2. Breakout above = BUY
        3. Breakdown below = SELL
        
        Returns:
            Series with signals
        """
        signals = pd.Series(0, index=df.index)
        
        # Identify opening range (first or_minutes)
        # This assumes df has datetime index
        if not isinstance(df.index, pd.DatetimeIndex):
            return signals
        
        # Get first or_minutes bars
        first_bars = df.iloc[:or_minutes]
        or_high = first_bars['high'].max()
        or_low = first_bars['low'].min()
        
        # After opening range, check for breakouts
        after_or = df.iloc[or_minutes:]
        
        # Breakout conditions
        breakout_high = (after_or['close'] > or_high) & (after_or['volume'] > after_or['volume'].rolling(20).mean() * 1.5)
        breakout_low = (after_or['close'] < or_low) & (after_or['volume'] > after_or['volume'].rolling(20).mean() * 1.5)
        
        signals.loc[breakout_high.index[breakout_high]] = 1
        signals.loc[breakout_low.index[breakout_low]] = -1
        
        return signals
    
    @staticmethod
    def supertrend_strategy(df: pd.DataFrame) -> pd.Series:
        """
        Supertrend Strategy - Intraday/Swing
        
        Entry:
        - LONG: Supertrend turns green (direction = 1)
        - SHORT: Supertrend turns red (direction = -1)
        
        Returns:
            Series with signals
        """
        signals = pd.Series(0, index=df.index)
        
        # Detect direction changes
        direction_change = df['supertrend_dir'].diff()
        
        signals[direction_change == 2] = 1   # Changed from -1 to 1 (buy)
        signals[direction_change == -2] = -1  # Changed from 1 to -1 (sell)
        
        return signals
    
    @staticmethod
    def rsi_mean_reversion(df: pd.DataFrame, oversold: int = 30, overbought: int = 70) -> pd.Series:
        """
        RSI Mean Reversion - Swing
        
        Entry:
        - LONG: RSI crosses above oversold level
        - SHORT: RSI crosses below overbought level
        
        Returns:
            Series with signals
        """
        signals = pd.Series(0, index=df.index)
        
        # Oversold bounce
        oversold_bounce = (df['rsi'] > oversold) & (df['rsi'].shift(1) <= oversold)
        
        # Overbought reversal
        overbought_reversal = (df['rsi'] < overbought) & (df['rsi'].shift(1) >= overbought)
        
        signals[oversold_bounce] = 1
        signals[overbought_reversal] = -1
        
        return signals
    
    @staticmethod
    def golden_cross(df: pd.DataFrame) -> pd.Series:
        """
        Golden Cross / Death Cross - Long-term
        
        Entry:
        - LONG: 50 SMA crosses above 200 SMA (Golden Cross)
        - SHORT: 50 SMA crosses below 200 SMA (Death Cross)
        
        Returns:
            Series with signals
        """
        signals = pd.Series(0, index=df.index)
        
        sma_50 = TechnicalIndicators.sma(df['close'], 50)
        sma_200 = TechnicalIndicators.sma(df['close'], 200)
        
        # Golden Cross
        golden_cross = (sma_50 > sma_200) & (sma_50.shift(1) <= sma_200.shift(1))
        
        # Death Cross
        death_cross = (sma_50 < sma_200) & (sma_50.shift(1) >= sma_200.shift(1))
        
        signals[golden_cross] = 1
        signals[death_cross] = -1
        
        return signals
    
    @staticmethod
    def bollinger_band_bounce(df: pd.DataFrame) -> pd.Series:
        """
        Bollinger Band Bounce - Mean Reversion
        
        Entry:
        - LONG: Price touches lower BB + RSI < 30
        - SHORT: Price touches upper BB + RSI > 70
        
        Returns:
            Series with signals
        """
        signals = pd.Series(0, index=df.index)
        
        # Touch lower band
        touch_lower = (df['close'] <= df['lower_bb'] * 1.01) & (df['rsi'] < 30)
        
        # Touch upper band
        touch_upper = (df['close'] >= df['upper_bb'] * 0.99) & (df['rsi'] > 70)
        
        signals[touch_lower] = 1
        signals[touch_upper] = -1
        
        return signals


# ============================================================================
# PART 4: COMPLETE TRADING SYSTEM
# ============================================================================

class CompleteTradingSystem:
    """
    Integrated trading system with indicators, strategies, and execution
    """
    
    def __init__(self, api_key: str = None, client_code: str = None, password: str = None):
        self.scrip_master = AngelScripMaster()
        self.indicators = TechnicalIndicators()
        self.strategies = TradingStrategies()
        
        # Load instruments on initialization
        self.scrip_master.load_cached_scrip_master()
        
        logger.info("✅ Trading System initialized")
    
    def get_stock_list(self, category: str = 'nifty50') -> List[Dict]:
        """
        Get stock list by category
        
        Args:
            category: 'nifty50', 'liquid', 'all_equity'
        
        Returns:
            List of stock dictionaries
        """
        if category == 'nifty50':
            return self.scrip_master.get_nifty50_stocks()
        elif category == 'liquid':
            df = self.scrip_master.get_liquid_stocks_for_intraday()
            return df.to_dict('records')
        else:
            df = self.scrip_master.instruments_df[
                (self.scrip_master.instruments_df['exch_seg'] == 'NSE') &
                (self.scrip_master.instruments_df['instrumenttype'] == 'EQ')
            ]
            return df[['token', 'symbol', 'name']].to_dict('records')
    
    def analyze_stock(self, symbol: str, timeframe: str = '5minute') -> Dict:
        """
        Complete technical analysis of a stock
        
        Args:
            symbol: Stock symbol (e.g., "SBIN")
            timeframe: '1minute', '5minute', '15minute', 'day'
        
        Returns:
            Dict with analysis results
        """
        # Find token
        token_info = self.scrip_master.find_token(symbol, 'NSE')
        if token_info.empty:
            logger.error(f"Symbol {symbol} not found")
            return None
        
        token = token_info.iloc[0]['token']
        
        # TODO: Fetch historical data from Angel One API
        # df = self.fetch_historical_data(token, timeframe)
        
        # For now, return structure
        return {
            'symbol': symbol,
            'token': token,
            'analysis': {
                'trend': None,
                'momentum': None,
                'volatility': None,
                'signals': []
            }
        }
    
    def backtest_strategy(
        self,
        symbol: str,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000
    ) -> Dict:
        """
        Backtest a strategy on historical data
        
        Args:
            symbol: Stock symbol
            strategy_name: Name of strategy to test
            start_date: Start date YYYY-MM-DD
            end_date: End date YYYY-MM-DD
            initial_capital: Starting capital
        
        Returns:
            Dict with backtest results
        """
        logger.info(f"Backtesting {strategy_name} on {symbol}")
        
        # TODO: Implement full backtest engine
        # 1. Fetch historical data
        # 2. Calculate indicators
        # 3. Generate signals
        # 4. Simulate trades
        # 5. Calculate performance metrics
        
        return {
            'symbol': symbol,
            'strategy': strategy_name,
            'period': f"{start_date} to {end_date}",
            'results': {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        }
    
    def generate_stock_universe(self, criteria: Dict) -> pd.DataFrame:
        """
        Generate stock universe based on criteria
        
        Args:
            criteria: Dict with filters
                {
                    'min_price': 50,
                    'max_price': 5000,
                    'fo_only': True,
                    'exclude_sectors': ['Bank']
                }
        
        Returns:
            DataFrame with filtered stocks
        """
        df = self.scrip_master.instruments_df
        
        # Apply filters
        filtered = df[
            (df['exch_seg'] == 'NSE') &
            (df['instrumenttype'] == 'EQ')
        ].copy()
        
        if criteria.get('fo_only'):
            fo_stocks = df[df['exch_seg'] == 'NFO']['symbol'].str.replace('-EQ', '').unique()
            filtered = filtered[filtered['symbol'].str.replace('-EQ', '').isin(fo_stocks)]
        
        return filtered[['token', 'symbol', 'name']]


# ============================================================================
# PART 5: EXAMPLE USAGE & TESTING
# ============================================================================

def main():
    """
    Example usage of the complete system
    """
    logger.info("="*60)
    logger.info("COMPLETE TRADING SYSTEM - DEMONSTRATION")
    logger.info("="*60)
    
    # Initialize system
    system = CompleteTradingSystem()
    
    # 1. Download/Load Scrip Master
    logger.info("\n1️⃣ Loading Angel One Scrip Master...")
    scrip_master = system.scrip_master
    
    # 2. Get Nifty 50 stocks
    logger.info("\n2️⃣ Fetching Nifty 50 stocks...")
    nifty50 = system.get_stock_list('nifty50')
    logger.info(f"Found {len(nifty50)} Nifty 50 stocks")
    for stock in nifty50[:5]:
        logger.info(f"  {stock['symbol']}: Token {stock['token']}")
    
    # 3. Get liquid stocks for intraday
    logger.info("\n3️⃣ Fetching liquid stocks for intraday...")
    liquid = system.get_stock_list('liquid')
    logger.info(f"Found {len(liquid)} liquid F&O stocks")
    
    # 4. Search for specific symbols
    logger.info("\n4️⃣ Searching for specific symbols...")
    symbols_to_find = ['SBIN', 'RELIANCE', 'NIFTY', 'BANKNIFTY']
    for symbol in symbols_to_find:
        result = scrip_master.find_token(symbol, 'NSE' if symbol in ['SBIN', 'RELIANCE'] else 'NFO')
        if not result.empty:
            logger.info(f"  {symbol}: {result.iloc[0]['token']}")
    
    # 5. Get index tokens
    logger.info("\n5️⃣ Index tokens:")
    indices = scrip_master.get_index_tokens()
    for name, token in indices.items():
        logger.info(f"  {name}: {token}")
    
    # 6. Calculate indicators on sample data
    logger.info("\n6️⃣ Testing technical indicators on sample data...")
    
    # Create sample OHLCV data
    dates = pd.date_range(start='2024-01-01', periods=100, freq='5min')
    sample_df = pd.DataFrame({
        'datetime': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 102,
        'low': np.random.randn(100).cumsum() + 98,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000, 10000, 100)
    })
    sample_df.set_index('datetime', inplace=True)
    
    # Calculate all indicators
    sample_df = TechnicalIndicators.calculate_all_indicators(sample_df)
    logger.info("  ✅ Calculated: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, Supertrend, OBV")
    
    # 7. Test strategies
    logger.info("\n7️⃣ Testing trading strategies...")
    
    strategies_to_test = {
        'VWAP Scalping': TradingStrategies.vwap_scalping,
        'EMA Crossover': TradingStrategies.ema_crossover,
        'Supertrend': TradingStrategies.supertrend_strategy,
        'RSI Mean Reversion': TradingStrategies.rsi_mean_reversion,
        'Bollinger Band Bounce': TradingStrategies.bollinger_band_bounce,
    }
    
    for name, strategy_func in strategies_to_test.items():
        signals = strategy_func(sample_df)
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        logger.info(f"  {name}: {buy_signals} BUY, {sell_signals} SELL signals")
    
    # 8. Calculate pivot points
    logger.info("\n8️⃣ Calculating pivot points for today...")
    pivots = TechnicalIndicators.pivot_points(
        previous_high=17650,
        previous_low=17450,
        previous_close=17550
    )
    logger.info(f"  Pivot: {pivots['pivot']:.2f}")
    logger.info(f"  Resistance: R1={pivots['r1']:.2f}, R2={pivots['r2']:.2f}, R3={pivots['r3']:.2f}")
    logger.info(f"  Support: S1={pivots['s1']:.2f}, S2={pivots['s2']:.2f}, S3={pivots['s3']:.2f}")
    
    logger.info("\n" + "="*60)
    logger.info("✅ DEMONSTRATION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()

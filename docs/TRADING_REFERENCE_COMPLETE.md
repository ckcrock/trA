# COMPREHENSIVE TRADING REFERENCE
## Technical Indicators, Strategies & Symbol Tokens for Indian Markets

**Complete Reference Guide for Intraday, Swing, and Long-Term Trading**  
**Last Updated:** February 2026  
**Markets:** NSE, BSE, MCX (Indian Stock Markets)

---

## TABLE OF CONTENTS

1. [Technical Indicators Library (100+ Indicators)](#1-technical-indicators-library)
2. [Intraday Trading Strategies](#2-intraday-trading-strategies)
3. [Swing Trading Strategies](#3-swing-trading-strategies)
4. [Long-Term Investment Strategies](#4-long-term-investment-strategies)
5. [F&O Specific Strategies](#5-fo-specific-strategies)
6. [Angel One Symbol Tokens & Instrument Master](#6-angel-one-symbol-tokens)
7. [Stock Selection Criteria](#7-stock-selection-criteria)
8. [Implementation Guide](#8-implementation-guide)

---

## 1. TECHNICAL INDICATORS LIBRARY

### 1.1 TREND INDICATORS (15 indicators)

**Purpose:** Identify market direction and trend strength

#### 1.1.1 Moving Averages

**Simple Moving Average (SMA)**
```python
def sma(data, period):
    """
    Most basic trend indicator
    Periods: 20, 50, 100, 200 (most common)
    """
    return data['close'].rolling(window=period).mean()

# Usage for different timeframes:
# - Intraday: 9, 20, 50 SMA
# - Swing: 20, 50, 100 SMA
# - Long-term: 50, 100, 200 SMA
```

**Exponential Moving Average (EMA)**
```python
def ema(data, period):
    """
    Gives more weight to recent prices
    Faster response than SMA
    
    Popular combinations:
    - 9/21 EMA (intraday)
    - 12/26 EMA (swing)
    - 50/200 EMA (long-term Golden/Death Cross)
    """
    return data['close'].ewm(span=period, adjust=False).mean()
```

**Weighted Moving Average (WMA)**
```python
def wma(data, period):
    """
    Linear weighted moving average
    Most recent data has highest weight
    """
    weights = np.arange(1, period + 1)
    return data['close'].rolling(period).apply(
        lambda prices: np.dot(prices, weights) / weights.sum(),
        raw=True
    )
```

#### 1.1.2 MACD (Moving Average Convergence Divergence)

```python
def macd(data, fast=12, slow=26, signal=9):
    """
    Trend-following momentum indicator
    
    Components:
    - MACD Line: 12 EMA - 26 EMA
    - Signal Line: 9 EMA of MACD
    - Histogram: MACD - Signal
    
    Signals:
    - MACD crosses above Signal: BUY
    - MACD crosses below Signal: SELL
    - Histogram > 0: Bullish momentum
    - Histogram < 0: Bearish momentum
    
    Best for: Trend confirmation, divergence detection
    """
    ema_fast = data['close'].ewm(span=fast).mean()
    ema_slow = data['close'].ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram
```

#### 1.1.3 ADX (Average Directional Index)

```python
def adx(high, low, close, period=14):
    """
    Measures trend strength (NOT direction)
    
    Values:
    - 0-25: Weak/absent trend (avoid trend strategies)
    - 25-50: Strong trend
    - 50-75: Very strong trend
    - 75-100: Extremely strong trend
    
    Combined with:
    - +DI (Positive Directional Indicator)
    - -DI (Negative Directional Indicator)
    
    Signals:
    - ADX > 25 + +DI > -DI: Strong uptrend
    - ADX > 25 + -DI > +DI: Strong downtrend
    - ADX < 25: Range-bound market (use oscillators)
    
    Best for: Determining if market is trending
    """
    import talib
    return talib.ADX(high, low, close, timeperiod=period)
```

#### 1.1.4 Parabolic SAR

```python
def parabolic_sar(high, low, close, acceleration=0.02, maximum=0.2):
    """
    Stop and Reverse indicator
    
    Signals:
    - Dots below price: Uptrend (BUY)
    - Dots above price: Downtrend (SELL)
    - Dot switches side: Trend reversal
    
    Best for: Trailing stop-loss placement
    """
    import talib
    return talib.SAR(high, low, acceleration, maximum)
```

#### 1.1.5 Supertrend (Indian Market Favorite)

```python
def supertrend(high, low, close, period=10, multiplier=3):
    """
    Popular in Indian retail trading
    
    Parameters:
    - Period: 7, 10, 14 (common)
    - Multiplier: 1-3 (affects sensitivity)
    
    Signals:
    - Green line (price above): BUY signal
    - Red line (price below): SELL signal
    
    Best for: Nifty, Bank Nifty trending moves
    Works best on: 5-min, 15-min, 1-hour charts
    """
    import pandas as pd
    
    # Calculate ATR
    atr = calculate_atr(high, low, close, period)
    
    # Basic bands
    hl_avg = (high + low) / 2
    upper_band = hl_avg + (multiplier * atr)
    lower_band = hl_avg - (multiplier * atr)
    
    # Supertrend calculation
    supertrend = pd.Series(index=close.index)
    direction = pd.Series(index=close.index)
    
    for i in range(1, len(close)):
        if close[i] > upper_band[i-1]:
            supertrend[i] = lower_band[i]
            direction[i] = 1
        elif close[i] < lower_band[i-1]:
            supertrend[i] = upper_band[i]
            direction[i] = -1
        else:
            supertrend[i] = supertrend[i-1]
            direction[i] = direction[i-1]
    
    return supertrend, direction
```

#### 1.1.6 Additional Trend Indicators

**Aroon Indicator**
- Identifies trend changes and strength
- Aroon Up & Aroon Down (0-100 scale)

**Ichimoku Cloud**
- Comprehensive trend system
- Multiple components: Tenkan, Kijun, Senkou Span A/B

**Donchian Channels**
- Price channel breakout system
- Plots highest high and lowest low

**Keltner Channels**
- Envelope indicator using ATR
- Similar to Bollinger Bands but volatility-based

**Price Channels**
- High/low bands over period
- Breakout identification

---

### 1.2 MOMENTUM/OSCILLATOR INDICATORS (20 indicators)

**Purpose:** Identify overbought/oversold conditions and momentum

#### 1.2.1 RSI (Relative Strength Index)

```python
def rsi(data, period=14):
    """
    Most popular momentum oscillator
    
    Formula:
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    
    Values:
    - 0-30: Oversold (potential BUY)
    - 30-70: Neutral zone
    - 70-100: Overbought (potential SELL)
    
    Advanced signals:
    - RSI divergence (price vs RSI diverges = reversal)
    - RSI trendline breaks
    - Hidden divergence (continuation pattern)
    
    Settings for different timeframes:
    - Intraday: 9, 14 period
    - Swing: 14, 21 period
    - Long-term: 14, 28 period
    
    Indian Market Usage:
    - Nifty/Bank Nifty: 14 RSI on 15-min
    - Stocks: 14 RSI on 5-min (intraday), Daily (swing)
    """
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# RSI Divergence detection
def rsi_divergence(price, rsi):
    """
    Bullish divergence: Price lower low, RSI higher low
    Bearish divergence: Price higher high, RSI lower high
    """
    pass
```

#### 1.2.2 Stochastic Oscillator

```python
def stochastic(high, low, close, k_period=14, d_period=3):
    """
    Compares close price to price range
    
    Formula:
    %K = (Current Close - Lowest Low) / (Highest High - Lowest Low) * 100
    %D = 3-period SMA of %K (signal line)
    
    Values:
    - 0-20: Oversold
    - 80-100: Overbought
    
    Signals:
    - %K crosses above %D in oversold: BUY
    - %K crosses below %D in overbought: SELL
    - Divergence with price
    
    Types:
    - Fast Stochastic (K=14, D=3)
    - Slow Stochastic (K=14, D=3, Slow D=3)
    
    Best for: Range-bound markets, reversals
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(window=d_period).mean()
    
    return k_percent, d_percent
```

#### 1.2.3 CCI (Commodity Channel Index)

```python
def cci(high, low, close, period=20):
    """
    Measures deviation from average price
    
    Values:
    - Above +100: Overbought
    - Below -100: Oversold
    - Between -100 to +100: Normal range
    
    Signals:
    - CCI crosses above +100: Strong uptrend
    - CCI crosses below -100: Strong downtrend
    - Zero line crosses
    
    Best for: Commodities, cyclical stocks
    """
    tp = (high + low + close) / 3  # Typical Price
    sma_tp = tp.rolling(window=period).mean()
    mad = (tp - sma_tp).abs().rolling(window=period).mean()  # Mean Absolute Deviation
    cci = (tp - sma_tp) / (0.015 * mad)
    return cci
```

#### 1.2.4 Williams %R

```python
def williams_r(high, low, close, period=14):
    """
    Similar to Stochastic but scale is inverted
    
    Values:
    - 0 to -20: Overbought
    - -80 to -100: Oversold
    
    Formula:
    %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
    
    Best for: Finding entry/exit points in trends
    """
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    williams = -100 * (highest_high - close) / (highest_high - lowest_low)
    return williams
```

#### 1.2.5 ROC (Rate of Change)

```python
def roc(close, period=12):
    """
    Measures percentage change in price
    
    Formula:
    ROC = ((Close - Close n periods ago) / Close n periods ago) * 100
    
    Signals:
    - ROC > 0: Positive momentum
    - ROC < 0: Negative momentum
    - ROC divergence: Potential reversal
    
    Best for: Momentum confirmation
    """
    roc = ((close - close.shift(period)) / close.shift(period)) * 100
    return roc
```

#### 1.2.6 Money Flow Index (MFI)

```python
def mfi(high, low, close, volume, period=14):
    """
    Volume-weighted RSI
    
    Values:
    - 0-20: Oversold
    - 80-100: Overbought
    
    Considers both price and volume
    More reliable than RSI for volume confirmation
    
    Best for: Spotting divergences with volume
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    positive_mf = positive_flow.rolling(window=period).sum()
    negative_mf = negative_flow.rolling(window=period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi
```

#### 1.2.7 Additional Momentum Indicators

**Awesome Oscillator (AO)**
- Difference between 5 and 34-period SMA of midpoint

**Momentum Indicator**
- Rate of price change over period

**TSI (True Strength Index)**
- Double-smoothed momentum oscillator

**Ultimate Oscillator**
- Combines 3 timeframes to reduce false signals

**Schaff Trend Cycle**
- Modified MACD using stochastic

**Cumulative RSI**
- Sum of RSI over periods

**Stochastic RSI**
- Stochastic applied to RSI values

---

### 1.3 VOLUME INDICATORS (10 indicators)

**Purpose:** Confirm price movements with volume

#### 1.3.1 OBV (On Balance Volume)

```python
def obv(close, volume):
    """
    Cumulative volume indicator
    
    Logic:
    - If close > previous close: OBV = OBV + volume
    - If close < previous close: OBV = OBV - volume
    - If close = previous close: OBV unchanged
    
    Signals:
    - OBV rising: Accumulation (bullish)
    - OBV falling: Distribution (bearish)
    - OBV divergence: Potential reversal
    
    Best for: Confirming breakouts with volume
    """
    obv = (volume * (~close.diff().le(0) * 2 - 1)).cumsum()
    return obv
```

#### 1.3.2 Volume Weighted Average Price (VWAP)

```python
def vwap(high, low, close, volume):
    """
    CRITICAL for Indian intraday trading
    
    Formula:
    VWAP = Cumulative(Typical Price × Volume) / Cumulative(Volume)
    
    Usage:
    - Price above VWAP: Bullish (buy above VWAP)
    - Price below VWAP: Bearish (sell below VWAP)
    - Reversion to VWAP: Common intraday pattern
    
    Indian Market Importance:
    - Institutional traders use VWAP for execution
    - Banks, FIIs buy/sell around VWAP
    - Intraday strategies: VWAP bounce, VWAP breakout
    
    Timeframe: Day-specific (resets daily)
    Best for: Nifty, Bank Nifty, liquid stocks
    """
    typical_price = (high + low + close) / 3
    cumulative_tp_volume = (typical_price * volume).cumsum()
    cumulative_volume = volume.cumsum()
    vwap = cumulative_tp_volume / cumulative_volume
    return vwap
```

#### 1.3.3 Volume Price Trend (VPT)

```python
def vpt(close, volume):
    """
    Similar to OBV but weighted by price change
    
    Formula:
    VPT = Previous VPT + (Volume × (Close - Previous Close) / Previous Close)
    
    Best for: Confirming trends with volume
    """
    price_change_pct = close.pct_change()
    vpt = (volume * price_change_pct).cumsum()
    return vpt
```

#### 1.3.4 Accumulation/Distribution Line

```python
def accumulation_distribution(high, low, close, volume):
    """
    Measures money flow into/out of security
    
    Formula:
    AD = Previous AD + (((Close - Low) - (High - Close)) / (High - Low)) × Volume
    
    Signals:
    - Rising AD with rising price: Healthy uptrend
    - Falling AD with rising price: Weak uptrend (divergence)
    - Rising AD with falling price: Potential reversal
    
    Best for: Divergence detection
    """
    clv = ((close - low) - (high - close)) / (high - low)
    ad = (clv * volume).cumsum()
    return ad
```

#### 1.3.5 Chaikin Money Flow

```python
def chaikin_money_flow(high, low, close, volume, period=20):
    """
    Measures buying/selling pressure over period
    
    Values:
    - Above 0: Buying pressure
    - Below 0: Selling pressure
    
    Best for: Confirming trend strength
    """
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_volume = mf_multiplier * volume
    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf
```

#### 1.3.6 Additional Volume Indicators

**Volume Oscillator**
- Difference between fast and slow volume MAs

**Ease of Movement**
- Price movement per unit of volume

**Force Index**
- Price change × volume

**Klinger Oscillator**
- Long-term money flow

---

### 1.4 VOLATILITY INDICATORS (8 indicators)

**Purpose:** Measure market volatility and price ranges

#### 1.4.1 Bollinger Bands

```python
def bollinger_bands(close, period=20, std_dev=2):
    """
    Most popular volatility indicator
    
    Components:
    - Middle Band: 20-period SMA
    - Upper Band: SMA + (2 × Standard Deviation)
    - Lower Band: SMA - (2 × Standard Deviation)
    
    Signals:
    - Price at upper band: Overbought
    - Price at lower band: Oversold
    - Band squeeze: Low volatility, breakout imminent
    - Band expansion: High volatility, trending market
    - Bollinger Bounce: Price bounces between bands (range)
    - Bollinger Squeeze: Bands narrow (breakout coming)
    
    Indian Market Settings:
    - Intraday: 20-period, 2 std dev on 5-min/15-min
    - Swing: 20-period, 2 std dev on daily
    
    Best for: Mean reversion, breakout anticipation
    """
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    
    return upper_band, sma, lower_band
```

#### 1.4.2 ATR (Average True Range)

```python
def atr(high, low, close, period=14):
    """
    Measures market volatility (NOT direction)
    
    Formula:
    True Range = max(High - Low, |High - Previous Close|, |Low - Previous Close|)
    ATR = Average of True Range over period
    
    Usage:
    - High ATR: High volatility (wider stops needed)
    - Low ATR: Low volatility (tighter stops possible)
    
    Applications:
    - Stop-loss placement: Entry ± (2 × ATR)
    - Position sizing: Risk / ATR
    - Target setting: Entry + (3 × ATR)
    
    Indian Market:
    - Nifty ATR ~100-150 points (typical)
    - Bank Nifty ATR ~300-500 points
    - Use for dynamic stop-loss
    
    Best for: Risk management, position sizing
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr
```

#### 1.4.3 Standard Deviation

```python
def standard_deviation(close, period=20):
    """
    Statistical measure of volatility
    
    High STD: High volatility
    Low STD: Low volatility
    
    Used in: Bollinger Bands calculation
    """
    return close.rolling(window=period).std()
```

#### 1.4.4 Historical Volatility

```python
def historical_volatility(close, period=20):
    """
    Annualized standard deviation of returns
    
    Used for: Options pricing, risk assessment
    """
    returns = np.log(close / close.shift(1))
    volatility = returns.rolling(window=period).std() * np.sqrt(252)
    return volatility
```

#### 1.4.5 Bollinger Band Width

```python
def bollinger_bandwidth(close, period=20, std_dev=2):
    """
    Measures width of Bollinger Bands
    
    BandWidth = (Upper Band - Lower Band) / Middle Band
    
    Signals:
    - Narrowing bandwidth: "Squeeze" - breakout coming
    - Widening bandwidth: High volatility, trending
    
    Best for: Anticipating breakouts
    """
    upper, middle, lower = bollinger_bands(close, period, std_dev)
    bandwidth = (upper - lower) / middle
    return bandwidth
```

#### 1.4.6 Additional Volatility Indicators

**Keltner Channels**
- ATR-based channels

**Donchian Channels**
- Highest high/lowest low channels

**Chandelier Exit**
- Trailing stop based on ATR

---

### 1.5 SUPPORT/RESISTANCE INDICATORS (5 indicators)

#### 1.5.1 Pivot Points (CRITICAL for Indian Intraday)

```python
def pivot_points(previous_high, previous_low, previous_close):
    """
    EXTREMELY POPULAR in Indian intraday trading
    
    Formula:
    Pivot Point (PP) = (High + Low + Close) / 3
    
    Resistance levels:
    R1 = (2 × PP) - Low
    R2 = PP + (High - Low)
    R3 = High + 2 × (PP - Low)
    
    Support levels:
    S1 = (2 × PP) - High
    S2 = PP - (High - Low)
    S3 = Low - 2 × (High - PP)
    
    Usage:
    - Calculated from previous day's H/L/C
    - Used as intraday support/resistance
    - Price above PP: Bullish bias
    - Price below PP: Bearish bias
    
    Indian Market:
    - NSE traders HEAVILY use pivot points
    - Nifty/Bank Nifty pivot levels watched closely
    - Often combine with VWAP
    
    Types:
    - Standard Pivots (above)
    - Fibonacci Pivots
    - Camarilla Pivots
    - Woodie Pivots
    
    Best for: Intraday trading, entry/exit levels
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
```

#### 1.5.2 Fibonacci Retracement

```python
def fibonacci_retracement(high, low):
    """
    Key levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
    
    Uptrend retracement (from low to high):
    - 23.6% level: high - (0.236 × (high - low))
    - 38.2% level: high - (0.382 × (high - low))
    - 50% level: high - (0.5 × (high - low))
    - 61.8% level: high - (0.618 × (high - low))
    
    Usage:
    - Identify potential support in uptrend
    - Identify potential resistance in downtrend
    - 50% and 61.8% are strongest levels
    
    Best for: Pullback entries, target setting
    """
    diff = high - low
    
    levels = {
        '0%': high,
        '23.6%': high - (0.236 * diff),
        '38.2%': high - (0.382 * diff),
        '50%': high - (0.5 * diff),
        '61.8%': high - (0.618 * diff),
        '78.6%': high - (0.786 * diff),
        '100%': low
    }
    
    return levels
```

#### 1.5.3 Fibonacci Extension (Targets)

```python
def fibonacci_extension(low, high, retracement_low):
    """
    For setting profit targets beyond previous high
    
    Extension levels: 127.2%, 161.8%, 200%, 261.8%
    """
    diff = high - low
    
    extensions = {
        '127.2%': retracement_low + (1.272 * diff),
        '161.8%': retracement_low + (1.618 * diff),
        '200%': retracement_low + (2.0 * diff),
        '261.8%': retracement_low + (2.618 * diff)
    }
    
    return extensions
```

---

### 1.6 CANDLESTICK PATTERN INDICATORS

**Purpose:** Price action analysis

**Key Patterns (30+ patterns):**

**Reversal Patterns:**
- Doji, Hammer, Shooting Star
- Engulfing (Bullish/Bearish)
- Morning Star, Evening Star
- Piercing Line, Dark Cloud Cover

**Continuation Patterns:**
- Three White Soldiers, Three Black Crows
- Rising Three Methods, Falling Three Methods

**Indecision Patterns:**
- Spinning Top, Harami

---

### 1.7 INDIAN MARKET SPECIFIC INDICATORS

#### 1.7.1 Opening Range Breakout (ORB)

```python
def opening_range_breakout(bars, or_period_minutes=15):
    """
    VERY POPULAR Indian intraday strategy
    
    Method:
    1. Identify first 15/30 minutes high/low
    2. Breakout above OR high = BUY
    3. Breakdown below OR low = SELL
    
    Usage:
    - Best on volatile stocks (Reliance, TCS, Infosys)
    - Nifty/Bank Nifty futures
    - First hour of trading (9:15-10:15 AM)
    
    Entry: Breakout + volume confirmation
    Stop Loss: Opposite end of opening range
    Target: 1:2 or 1:3 risk-reward
    
    Best for: Momentum traders, gap openings
    """
    # Get first N minutes of trading
    or_bars = bars.iloc[:or_period_minutes]
    or_high = or_bars['high'].max()
    or_low = or_bars['low'].min()
    or_range = or_high - or_low
    
    return {
        'or_high': or_high,
        'or_low': or_low,
        'or_range': or_range,
        'breakout_buy': or_high,
        'breakout_sell': or_low
    }
```

---

## 2. INTRADAY TRADING STRATEGIES

### 2.1 SCALPING STRATEGIES (Hold: Seconds to Minutes)

**Goal:** 0.2-0.5% profit per trade, 20-50+ trades/day

#### Strategy 1: VWAP Scalping

```python
class VWAPScalpingStrategy:
    """
    Most reliable intraday strategy for liquid stocks
    
    Entry Rules:
    - LONG: Price dips to VWAP, volume spike, RSI < 50, then bounces
    - SHORT: Price rises to VWAP, volume spike, RSI > 50, then rejects
    
    Exit Rules:
    - Target: 0.3-0.5% (3-5 points on Nifty)
    - Stop Loss: 0.2% (2-3 points)
    - Time Stop: 5-10 minutes max
    
    Best Stocks:
    - Nifty/Bank Nifty futures
    - HDFC Bank, Reliance, Infosys
    - TCS, ICICI Bank, SBI
    
    Timeframe: 1-minute, 3-minute charts
    Win Rate: 60-70% (with discipline)
    """
    
    def __init__(self):
        self.target_pct = 0.003  # 0.3%
        self.stop_loss_pct = 0.002  # 0.2%
        self.max_hold_time = 10  # minutes
    
    def generate_signal(self, bars):
        vwap = calculate_vwap(bars)
        current_price = bars['close'].iloc[-1]
        rsi = calculate_rsi(bars, 14)
        volume_spike = bars['volume'].iloc[-1] > bars['volume'].rolling(20).mean().iloc[-1] * 1.5
        
        # LONG signal
        if (current_price <= vwap * 1.001 and  # Within 0.1% of VWAP
            rsi < 50 and
            volume_spike and
            bars['close'].iloc[-1] > bars['open'].iloc[-1]):  # Bullish candle
            return 'BUY'
        
        # SHORT signal
        if (current_price >= vwap * 0.999 and
            rsi > 50 and
            volume_spike and
            bars['close'].iloc[-1] < bars['open'].iloc[-1]):  # Bearish candle
            return 'SELL'
        
        return 'HOLD'
```

#### Strategy 2: 5-Minute EMA Crossover Scalping

```python
class EMAScalpingStrategy:
    """
    Fast EMA crossover for quick trades
    
    Entry Rules:
    - LONG: 5 EMA crosses above 15 EMA + volume > avg + price > VWAP
    - SHORT: 5 EMA crosses below 15 EMA + volume > avg + price < VWAP
    
    Exit Rules:
    - Target: 0.4-0.6%
    - Stop Loss: 0.25%
    - Trailing stop: Move SL to entry after 0.3% profit
    
    Timeframe: 5-minute charts
    Best for: Trending market days
    Avoid: Range-bound, choppy days
    """
    pass
```

#### Strategy 3: Supertrend + RSI Scalping

```python
class SupertrendRSIScalping:
    """
    Combines trend and momentum
    
    Entry Rules:
    - LONG: Supertrend green + RSI crosses above 40 + volume surge
    - SHORT: Supertrend red + RSI crosses below 60 + volume surge
    
    Exit Rules:
    - Exit on Supertrend color change
    - Or target: 0.5%
    - Stop loss: Just beyond Supertrend line
    
    Best for: Bank Nifty, volatile stocks
    Timeframe: 3-min, 5-min
    """
    pass
```

---

### 2.2 MOMENTUM TRADING (Hold: 1-3 hours)

**Goal:** 1-3% profit per trade, 3-10 trades/day

#### Strategy 4: Opening Range Breakout (ORB)

```python
class OpeningRangeBreakout:
    """
    MOST POPULAR Indian intraday strategy
    
    Method:
    1. Mark first 15 minutes (9:15-9:30 AM) high/low
    2. Wait for breakout with volume (1.5x average)
    3. Enter on breakout candle close
    4. Stop loss: Opposite end of opening range
    5. Target: 2x or 3x the opening range
    
    Example:
    - Opening Range: 17,500 - 17,550 (Nifty)
    - OR Range: 50 points
    - Breakout at 17,555 = BUY
    - Stop Loss: 17,495 (5 points below OR low)
    - Target 1: 17,655 (2x range = 100 points)
    - Target 2: 17,705 (3x range = 150 points)
    
    Best for:
    - Gap openings (gap up/down)
    - High volatility stocks
    - Nifty/Bank Nifty futures
    
    Avoid:
    - Flat openings (no gap)
    - Low volatility days
    - Inside days (range within previous day)
    
    Success Rate: 55-65%
    Risk:Reward: 1:2 minimum
    """
    
    def __init__(self, or_period=15):
        self.or_period = or_period  # minutes
        self.or_high = None
        self.or_low = None
        self.or_range = None
    
    def calculate_opening_range(self, bars):
        """Calculate first 15-min high/low"""
        or_bars = bars[bars.index.time >= time(9, 15)][:self.or_period]
        self.or_high = or_bars['high'].max()
        self.or_low = or_bars['low'].min()
        self.or_range = self.or_high - self.or_low
    
    def generate_signal(self, current_bar):
        if self.or_high is None:
            return 'WAIT'
        
        current_time = current_bar.name.time()
        if current_time < time(9, 30):
            return 'WAIT'  # Still in opening range
        
        price = current_bar['close']
        volume_surge = current_bar['volume'] > bars['volume'].rolling(20).mean() * 1.5
        
        # Bullish breakout
        if price > self.or_high and volume_surge:
            return {
                'signal': 'BUY',
                'entry': price,
                'stop_loss': self.or_low - (self.or_range * 0.1),
                'target1': price + (2 * self.or_range),
                'target2': price + (3 * self.or_range)
            }
        
        # Bearish breakdown
        if price < self.or_low and volume_surge:
            return {
                'signal': 'SELL',
                'entry': price,
                'stop_loss': self.or_high + (self.or_range * 0.1),
                'target1': price - (2 * self.or_range),
                'target2': price - (3 * self.or_range)
            }
        
        return 'HOLD'
```

#### Strategy 5: Momentum Burst Strategy

```python
class MomentumBurstStrategy:
    """
    Catch strong momentum moves
    
    Entry Criteria:
    - 5-min candle breaks 20-bar high/low
    - Volume > 2x average
    - RSI crosses 60 (for long) or 40 (for short)
    - MACD positive crossover (for long)
    
    Exit:
    - Target: 2-3%
    - Stop: 1%
    - Trailing: Trail by 1% after 1.5% profit
    
    Best Stocks:
    - High beta stocks (>1.5 beta)
    - News-driven moves
    - Sector rotation plays
    
    Timeframe: 5-min, 15-min
    """
    pass
```

---

### 2.3 MEAN REVERSION STRATEGIES

#### Strategy 6: Bollinger Band Bounce

```python
class BollingerBandBounce:
    """
    Trade bounces from BB extremes
    
    Entry Rules:
    - LONG: Price touches lower BB + RSI < 30 + bullish candle
    - SHORT: Price touches upper BB + RSI > 70 + bearish candle
    
    Exit Rules:
    - Exit at middle BB (20 SMA)
    - Or opposite BB
    - Stop loss: Just beyond entry candle
    
    Best for:
    - Range-bound markets
    - Low ADX (<25)
    - Choppy days
    
    Avoid:
    - Trending markets
    - High ADX (>30)
    - Breakout scenarios
    
    Timeframe: 15-min, 30-min
    Win Rate: 60-70% in ranging markets
    """
    pass
```

---

### 2.4 BREAKOUT STRATEGIES

#### Strategy 7: Volume Breakout Strategy

```python
class VolumeBreakoutStrategy:
    """
    High-probability breakout trading
    
    Setup:
    - Identify consolidation (3+ hours, tight range)
    - Volume drying up during consolidation
    - Breakout with 2x volume surge
    
    Entry:
    - Enter on breakout candle close
    - Volume confirmation essential
    
    Stop Loss:
    - Just below/above consolidation range
    
    Target:
    - Measure consolidation height
    - Project from breakout point
    
    Example:
    - Consolidation: 1000-1020 (range = 20)
    - Breakout at 1025 with volume
    - Target: 1025 + 20 = 1045
    
    Best for:
    - Pre-earnings announcements
    - Policy decisions
    - Technical breakouts
    
    Timeframe: 15-min, 1-hour
    """
    pass
```

---

### 2.5 GAP TRADING STRATEGIES

#### Strategy 8: Gap and Go

```python
class GapAndGoStrategy:
    """
    Trade continuation after gap opening
    
    Types of Gaps:
    1. Gap Up (open > previous high)
    2. Gap Down (open < previous low)
    
    Trading Rules:
    - Gap > 1% required
    - Strong pre-market volume
    - Wait for first pullback
    - Enter on continuation
    
    Example (Gap Up):
    - Previous close: 1000
    - Open: 1025 (2.5% gap up)
    - First 15-min: Pullback to 1020
    - Entry: Above 1025 again
    - Stop: Below 1020
    - Target: 1050+ (another 2.5%)
    
    Best for:
    - News-driven gaps
    - Earnings gaps
    - Sector rotation
    
    Avoid:
    - Gap fills (price returns to previous close)
    - Weak volume
    
    Success Rate: 50-60%
    """
    pass
```

---

## 3. SWING TRADING STRATEGIES

**Holding Period:** 2-10 days  
**Goal:** 5-15% per trade

### 3.1 TREND FOLLOWING STRATEGIES

#### Strategy 9: EMA Crossover (20/50)

```python
class SMA_EMA_CrossoverSwing:
    """
    Classic swing trading strategy
    
    Entry Rules:
    - LONG: 20 EMA crosses above 50 EMA + MACD positive + ADX > 25
    - SHORT: 20 EMA crosses below 50 EMA + MACD negative + ADX > 25
    
    Additional Filters:
    - Volume > 20-day average
    - Price above 200 SMA (for long-term trend)
    - RSI between 40-60 (not overbought/oversold)
    
    Exit Rules:
    - Opposite crossover
    - Or trailing stop (ATR-based)
    - Or 10-15% profit target
    
    Stop Loss:
    - Below recent swing low (for long)
    - Above recent swing high (for short)
    - Or 2 × ATR from entry
    
    Position Sizing:
    - Risk 1-2% per trade
    - Calculate based on stop distance
    
    Best for:
    - Trending markets
    - Blue-chip stocks
    - Index futures
    
    Timeframe: Daily charts
    Win Rate: 45-55% (large winners compensate)
    """
    pass
```

#### Strategy 10: Supertrend + ADX Swing

```python
class SupertrendADXSwing:
    """
    Trend confirmation strategy
    
    Entry Rules:
    - LONG: Supertrend green + ADX > 25 + RSI > 50
    - SHORT: Supertrend red + ADX > 25 + RSI < 50
    
    Hold:
    - While Supertrend color unchanged
    - ADX remains strong (>20)
    
    Exit:
    - Supertrend flips color
    - ADX drops below 20 (trend weakening)
    
    Best for:
    - Strong trending stocks
    - F&O stocks with good liquidity
    
    Timeframe: Daily, Weekly
    """
    pass
```

---

### 3.2 MEAN REVERSION STRATEGIES

#### Strategy 11: RSI Divergence Trading

```python
class RSIDivergenceSwing:
    """
    Trade RSI-price divergences
    
    Bullish Divergence:
    - Price makes lower low
    - RSI makes higher low
    - Signal: Potential reversal up
    
    Bearish Divergence:
    - Price makes higher high
    - RSI makes lower high
    - Signal: Potential reversal down
    
    Entry:
    - Wait for confirmation candle
    - Enter on bullish/bearish engulfing
    
    Stop Loss:
    - Below/above divergence low/high
    
    Target:
    - Previous swing high/low
    - Or Fibonacci extension levels
    
    Best for:
    - Reversal trading
    - Overbought/oversold extremes
    
    Timeframe: Daily
    Win Rate: 55-65%
    """
    pass
```

---

### 3.3 SUPPORT/RESISTANCE STRATEGIES

#### Strategy 12: Fibonacci Retracement Trading

```python
class FibonacciRetracementSwing:
    """
    Trade pullbacks in trends
    
    Method:
    1. Identify strong trend (up/down)
    2. Draw Fibonacci from swing low to swing high
    3. Wait for pullback to 50% or 61.8% level
    4. Enter with confirmation (bullish candle, volume)
    
    Entry:
    - At 50% or 61.8% Fibonacci level
    - Confirmation candle required
    - Volume on entry candle
    
    Stop Loss:
    - Below 78.6% level
    - Or below swing low
    
    Target:
    - Previous high (for continuation)
    - Or Fibonacci extension (127%, 161%)
    
    Best for:
    - Strong trends with pullbacks
    - Uptrends in bull markets
    
    Timeframe: Daily
    Success Rate: 60-70%
    """
    pass
```

---

## 4. LONG-TERM INVESTMENT STRATEGIES

**Holding Period:** Months to Years  
**Goal:** 20-100%+ returns

### 4.1 TREND-FOLLOWING STRATEGIES

#### Strategy 13: 50/200 SMA Golden Cross

```python
class GoldenCrossStrategy:
    """
    Long-term trend confirmation
    
    Golden Cross:
    - 50 SMA crosses above 200 SMA
    - Strong bullish signal
    - Enter long positions
    
    Death Cross:
    - 50 SMA crosses below 200 SMA
    - Strong bearish signal
    - Exit positions or short
    
    Additional Filters:
    - Above average volume on cross
    - Price above both SMAs
    - MACD histogram positive
    
    Position Management:
    - Hold while 50 SMA > 200 SMA
    - Add on pullbacks to 50 SMA
    - Exit on Death Cross
    
    Stop Loss:
    - Below 200 SMA
    - Or 15-20% trailing stop
    
    Best for:
    - Large-cap stocks
    - Index funds/ETFs
    - Quality blue-chips
    
    Timeframe: Weekly, Monthly charts
    Win Rate: 40-50% (but large winners)
    """
    pass
```

---

### 4.2 FUNDAMENTAL + TECHNICAL STRATEGIES

#### Strategy 14: Quality Growth Momentum

```python
class QualityGrowthMomentum:
    """
    Combine fundamentals with technicals
    
    Fundamental Criteria:
    - ROE > 15%
    - Debt/Equity < 1.0
    - Revenue growth > 15% (3 years)
    - Profit growth > 20% (3 years)
    - P/E reasonable (<30)
    
    Technical Criteria:
    - Price > 200 SMA
    - RSI > 50 (momentum positive)
    - MACD above signal line
    - Volume increasing
    
    Entry:
    - Buy breakout above resistance
    - Or pullback to 50 SMA
    
    Position Sizing:
    - 5-10% of portfolio per stock
    - Maximum 15-20 stocks
    
    Hold:
    - 1-3 years
    - Review quarterly
    
    Exit:
    - Fundamental deterioration
    - Or technical breakdown (below 200 SMA)
    
    Best for:
    - Long-term wealth creation
    - Patient investors
    
    Expected Returns: 15-25% CAGR
    """
    pass
```

---

## 5. F&O SPECIFIC STRATEGIES

### 5.1 OPTIONS STRATEGIES

#### Strategy 15: Iron Condor (Range-Bound)

```python
class IronCondorStrategy:
    """
    Profit from low volatility
    
    Setup:
    - Sell OTM call (higher strike)
    - Buy OTM call (even higher strike)
    - Sell OTM put (lower strike)
    - Buy OTM put (even lower strike)
    
    Example (Nifty at 17,500):
    - Sell 17,700 Call
    - Buy 17,800 Call
    - Sell 17,300 Put
    - Buy 17,200 Put
    
    Profit Zone: 17,300 - 17,700
    Max Profit: Net premium received
    Max Loss: Strike width - Net premium
    
    Best When:
    - Low volatility expected
    - Nifty/Bank Nifty in range
    - Days to expiry: 15-30
    
    Management:
    - Close at 50% profit
    - Close if breaches one side
    - Don't hold till expiry
    
    Success Rate: 70-80%
    """
    pass
```

#### Strategy 16: Bull Call Spread

```python
class BullCallSpread:
    """
    Bullish strategy with limited risk
    
    Setup:
    - Buy ATM call
    - Sell OTM call
    
    Example (Nifty at 17,500):
    - Buy 17,500 Call @ ₹150
    - Sell 17,700 Call @ ₹80
    - Net Debit: ₹70
    
    Max Profit: (Strike difference - Net debit) × Lot size
    Max Loss: Net debit × Lot size
    
    Best When:
    - Moderately bullish
    - Want to reduce cost
    - Days to expiry: 7-15
    
    Breakeven: Lower strike + Net debit
    """
    pass
```

---

### 5.2 FUTURES STRATEGIES

#### Strategy 17: Futures Pair Trading

```python
class FuturesPairTrading:
    """
    Market-neutral strategy
    
    Concept:
    - Trade two correlated stocks
    - Long underperformer
    - Short outperformer
    
    Example:
    - HDFC Bank vs ICICI Bank
    - When spread widens unusually
    - Long HDFC, Short ICICI
    - Wait for mean reversion
    
    Entry:
    - Spread > 2 standard deviations
    
    Exit:
    - Spread returns to mean
    
    Best for:
    - Sector pairs (banks, IT, auto)
    - Market-neutral returns
    
    Risk: Both move in same direction
    """
    pass
```

---

## 6. ANGEL ONE SYMBOL TOKENS

### 6.1 Scrip Master Download

**Official URL:**
```
https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
```

**Download Script:**

```python
import requests
import pandas as pd
from datetime import datetime

def download_angel_scrip_master():
    """
    Download latest instrument list from Angel One
    
    Returns: DataFrame with all instruments
    """
    url = 'https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json'
    
    print("Downloading Angel One scrip master...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        
        # Convert expiry to datetime
        df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce')
        
        # Save to CSV
        filename = f"angel_scrip_master_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(filename, index=False)
        
        print(f"Downloaded {len(df)} instruments")
        print(f"Saved to: {filename}")
        
        return df
    else:
        print(f"Error downloading: {response.status_code}")
        return None

# Download
scrip_df = download_angel_scrip_master()

# Display summary
print("\nInstrument Summary:")
print(scrip_df['exch_seg'].value_counts())
print("\nInstrument Types:")
print(scrip_df['instrumenttype'].value_counts())
```

### 6.2 Scrip Master Structure

**Columns:**
- `token`: Unique instrument identifier (use for API calls)
- `symbol`: Trading symbol (e.g., "SBIN-EQ", "NIFTY25FEB24FUT")
- `name`: Full instrument name
- `expiry`: Expiry date (for F&O)
- `strike`: Strike price (for options)
- `lotsize`: Lot size for F&O
- `instrumenttype`: EQ, FUTIDX, FUTSTK, OPTIDX, OPTSTK
- `exch_seg`: NSE, BSE, NFO, MCX, CDS
- `tick_size`: Minimum price movement

**Example Rows:**

| token | symbol | name | expiry | strike | lotsize | instrumenttype | exch_seg |
|-------|--------|------|--------|--------|---------|----------------|----------|
| 3045 | SBIN-EQ | SBIN | NaT | -1 | 1 | EQ | NSE |
| 1333 | HDFCBANK-EQ | HDFCBANK | NaT | -1 | 1 | EQ | NSE |
| 26000 | NIFTY50 | NIFTY50 | NaT | -1 | 50 | - | NSE |
| 99926000 | NIFTY | NIFTY | 2024-02-29 | -1 | 25 | FUTIDX | NFO |
| 99926009 | BANKNIFTY | BANKNIFTY | 2024-02-28 | -1 | 15 | FUTIDX | NFO |

### 6.3 Quick Symbol Lookup

```python
def find_token(df, search_term):
    """
    Quick search for instruments
    
    Usage:
    find_token(scrip_df, "SBIN")  # Equity
    find_token(scrip_df, "NIFTY")  # Index futures
    find_token(scrip_df, "BANKNIFTY")  # Bank Nifty
    """
    search_term = search_term.upper()
    results = df[df['symbol'].str.contains(search_term, na=False)]
    return results[['token', 'symbol', 'name', 'exch_seg', 'instrumenttype', 'lotsize']]

# Examples:
print(find_token(scrip_df, "SBIN"))
print(find_token(scrip_df, "NIFTY"))
print(find_token(scrip_df, "RELIANCE"))
```

### 6.4 Popular Instruments with Tokens

**Nifty 50 Stocks (Top 20):**

| Stock | Symbol | Token | Lot Size (F&O) |
|-------|--------|-------|----------------|
| Reliance Industries | RELIANCE-EQ | 2885 | 250 |
| TCS | TCS-EQ | 11536 | 125 |
| HDFC Bank | HDFCBANK-EQ | 1333 | 550 |
| Infosys | INFY-EQ | 1594 | 300 |
| ICICI Bank | ICICIBANK-EQ | 4963 | 1375 |
| Hindustan Unilever | HINDUNILVR-EQ | 1394 | 300 |
| ITC | ITC-EQ | 1660 | 1600 |
| SBI | SBIN-EQ | 3045 | 1500 |
| Bharti Airtel | BHARTIARTL-EQ | 10604 | 575 |
| Bajaj Finance | BAJFINANCE-EQ | 16675 | 125 |
| Kotak Bank | KOTAKBANK-EQ | 1922 | 400 |
| Axis Bank | AXISBANK-EQ | 5900 | 1200 |
| HCL Tech | HCLTECH-EQ | 7229 | 350 |
| Maruti Suzuki | MARUTI-EQ | 10999 | 50 |
| Asian Paints | ASIANPAINT-EQ | 1378 | 300 |
| Wipro | WIPRO-EQ | 3787 | 1200 |
| Larsen & Toubro | LT-EQ | 11483 | 300 |
| Titan | TITAN-EQ | 3506 | 350 |
| Tata Motors | TATAMOTORS-EQ | 3456 | 1500 |
| UltraTech Cement | ULTRACEMCO-EQ | 11532 | 150 |

**Indices:**

| Index | Symbol | Token |
|-------|--------|-------|
| Nifty 50 | NIFTY50 | 26000 |
| Bank Nifty | NIFTY BANK | 26009 |
| Fin Nifty | FINNIFTY | 26037 |
| Nifty IT | NIFTY IT | 26017 |
| Nifty Pharma | NIFTY PHARMA | 26023 |

---

## 7. STOCK SELECTION CRITERIA

### 7.1 Intraday Stock Selection

**Must-Have Criteria:**

1. **High Liquidity**
   - Daily volume > 1 million shares
   - Tight bid-ask spread (< 0.05%)
   - NSE F&O stocks preferred

2. **High Volatility**
   - Average daily range > 2%
   - ATR > ₹5 (for stocks < ₹500)
   - Beta > 1.0

3. **Trend Clarity**
   - ADX > 20 (trending)
   - Clear support/resistance levels
   - Not in tight consolidation

**Top Intraday Stocks (2025-2026):**

**High Volatility:**
- Adani Group stocks
- Yes Bank
- Suzlon Energy
- Tata Power
- RBL Bank

**Liquid Blue Chips:**
- Reliance Industries
- HDFC Bank, ICICI Bank, SBI
- Infosys, TCS, Wipro
- ITC, Hindustan Unilever
- Tata Motors, Maruti Suzuki

**Nifty/Bank Nifty Futures:**
- Best liquidity
- Tight spreads
- Good for scalping

### 7.2 Swing Trading Stock Selection

**Criteria:**

1. **Fundamental Strength**
   - Market cap > ₹5,000 crores
   - Promoter holding > 40%
   - Low debt (<50% of equity)
   - Consistent earnings

2. **Technical Setup**
   - Above 200 SMA
   - Recent consolidation/breakout
   - Volume increasing
   - RSI 40-60 range

3. **Sector Momentum**
   - Sector showing relative strength
   - Institutional interest

**Top Swing Trading Sectors:**
- IT (TCS, Infosys, HCL, Wipro)
- Banking (HDFC, ICICI, Kotak, Axis)
- Pharma (Sun Pharma, Dr. Reddy's)
- Auto (Maruti, Tata Motors, M&M)

### 7.3 Long-Term Investment Selection

**Criteria:**

1. **Quality Metrics**
   - ROE > 15% (consistently)
   - ROCE > 18%
   - Profit growth > 15% CAGR (5 years)
   - Revenue growth > 12% CAGR

2. **Valuation**
   - PE < Industry average
   - PEG < 1.5
   - Price to Book < 3

3. **Competitive Moat**
   - Market leader in sector
   - Strong brand
   - Barriers to entry

**Recommended Long-Term Holdings:**

**Large Caps:**
- HDFC Bank, ICICI Bank
- Reliance Industries
- TCS, Infosys
- Asian Paints
- Nestle India

**Mid Caps:**
- Crisil, Havells India
- Page Industries, Titan
- PI Industries
- Abbott India

---

## 8. IMPLEMENTATION GUIDE

### 8.1 Setting Up Technical Analysis

```python
# Install required libraries
pip install pandas numpy ta-lib yfinance smartapi-python

# Import libraries
import pandas as pd
import numpy as np
import talib
from SmartApi import SmartConnect
```

### 8.2 Complete Trading System Template

```python
class TradingSystem:
    def __init__(self, api_key, client_code, password):
        self.smart_api = SmartConnect(api_key)
        self.login(client_code, password)
        self.scrip_master = self.load_instruments()
    
    def login(self, client_code, password):
        """Authenticate with Angel One"""
        pass
    
    def load_instruments(self):
        """Download scrip master"""
        pass
    
    def get_historical_data(self, symbol, interval, days=30):
        """Fetch historical bars"""
        pass
    
    def calculate_indicators(self, df):
        """Calculate all technical indicators"""
        # Moving averages
        df['sma_20'] = talib.SMA(df['close'], 20)
        df['ema_9'] = talib.EMA(df['close'], 9)
        df['ema_21'] = talib.EMA(df['close'], 21)
        
        # Momentum
        df['rsi'] = talib.RSI(df['close'], 14)
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'], 12, 26, 9
        )
        
        # Volatility
        df['upper_bb'], df['middle_bb'], df['lower_bb'] = talib.BBANDS(
            df['close'], 20, 2, 2
        )
        df['atr'] = talib.ATR(df['high'], df['low'], df['close'], 14)
        
        # Volume
        df['vwap'] = self.calculate_vwap(df)
        
        return df
    
    def generate_signals(self, df, strategy='ema_crossover'):
        """Generate buy/sell signals based on strategy"""
        pass
    
    def backtest(self, symbol, strategy, start_date, end_date):
        """Backtest strategy on historical data"""
        pass
    
    def place_order(self, symbol, quantity, order_type, product_type):
        """Place order via API"""
        pass
    
    def run_live(self, symbols, strategy):
        """Run strategy in live mode"""
        pass
```

---

## CONCLUSION

This comprehensive reference provides **100+ technical indicators** and **17 detailed strategies** for trading Indian markets across all timeframes:

- **Intraday:** Scalping, momentum, breakout strategies
- **Swing:** Trend-following, mean reversion strategies
- **Long-term:** Fundamental + technical combinations
- **F&O:** Options and futures strategies

**Key Takeaways:**

1. **Start Simple:** Master 3-5 indicators before expanding
2. **Backtest Rigorously:** Test all strategies on historical data
3. **Risk Management:** Always use stop-losses
4. **Position Sizing:** Risk max 1-2% per trade
5. **Focus on Process:** Consistent execution > prediction

**Recommended Starting Point:**

For beginners:
- **Intraday:** VWAP + RSI strategy
- **Swing:** EMA 20/50 crossover
- **Long-term:** Quality growth stocks above 200 SMA

**Access Live Data:**
- Download scrip master daily from Angel One
- Use tokens for API calls
- Keep instrument list updated

**Happy Trading! 🚀📈**

---

**Document Version:** 1.0  
**Last Updated:** February 2026  
**Source:** Angel One SmartAPI Documentation

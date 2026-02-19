"""
Technical indicators library for Indian market trading.
Reference: docs/trading_system_implementation.py, docs/TRADING_REFERENCE_COMPLETE.md
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# TREND INDICATORS
# ═══════════════════════════════════════════════════════════════════════

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def supertrend(
    df: pd.DataFrame,
    period: int = 10,
    multiplier: float = 3.0,
) -> pd.DataFrame:
    """
    Supertrend indicator — very popular for Indian intraday trading.
    Returns DataFrame with 'supertrend' and 'supertrend_direction' columns.
    Direction: 1 = bullish (price above), -1 = bearish (price below).
    """
    hl2 = (df["high"] + df["low"]) / 2
    atr_val = atr(df, period)

    upper_band = hl2 + (multiplier * atr_val)
    lower_band = hl2 - (multiplier * atr_val)

    st = pd.Series(np.nan, index=df.index)
    direction = pd.Series(1, index=df.index)

    for i in range(period, len(df)):
        # Adjust bands
        if lower_band.iloc[i] > lower_band.iloc[i - 1] or df["close"].iloc[i - 1] < lower_band.iloc[i - 1]:
            pass  # keep current lower_band
        else:
            lower_band.iloc[i] = lower_band.iloc[i - 1]

        if upper_band.iloc[i] < upper_band.iloc[i - 1] or df["close"].iloc[i - 1] > upper_band.iloc[i - 1]:
            pass  # keep current upper_band
        else:
            upper_band.iloc[i] = upper_band.iloc[i - 1]

        # Determine direction
        if i == period:
            if df["close"].iloc[i] <= upper_band.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = 1
        else:
            prev_dir = direction.iloc[i - 1]
            if prev_dir == -1 and df["close"].iloc[i] > upper_band.iloc[i]:
                direction.iloc[i] = 1
            elif prev_dir == 1 and df["close"].iloc[i] < lower_band.iloc[i]:
                direction.iloc[i] = -1
            else:
                direction.iloc[i] = prev_dir

        st.iloc[i] = lower_band.iloc[i] if direction.iloc[i] == 1 else upper_band.iloc[i]

    result = df.copy()
    result["supertrend"] = st
    result["supertrend_direction"] = direction
    return result


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Average Directional Index — measures trend strength.
    Returns DataFrame with 'adx', 'plus_di', 'minus_di' columns.
    ADX > 25 = strong trend, ADX < 20 = weak/ranging.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    atr_val = atr(df, period)

    plus_di = 100 * ema(plus_dm, period) / atr_val
    minus_di = 100 * ema(minus_dm, period) / atr_val

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_val = ema(dx, period)

    result = df.copy()
    result["adx"] = adx_val
    result["plus_di"] = plus_di
    result["minus_di"] = minus_di
    return result


# ═══════════════════════════════════════════════════════════════════════
# MOMENTUM INDICATORS
# ═══════════════════════════════════════════════════════════════════════

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    RSI > 70 = overbought, RSI < 30 = oversold.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD — Moving Average Convergence Divergence.
    Returns (macd_line, signal_line, histogram).
    """
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator (%K, %D).
    %K > 80 = overbought, %K < 20 = oversold.
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return k, d


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = sma(tp, period)
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    return (tp - sma_tp) / (0.015 * mad)


def roc(series: pd.Series, period: int = 12) -> pd.Series:
    """Rate of Change — percentage change over N periods."""
    return ((series - series.shift(period)) / series.shift(period)) * 100


# ═══════════════════════════════════════════════════════════════════════
# VOLATILITY INDICATORS
# ═══════════════════════════════════════════════════════════════════════

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Average True Range — measures volatility.
    Used for stop-loss placement and position sizing.
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands — (upper, middle, lower).
    Width shows volatility, squeeze indicates breakout potential.
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


def bollinger_bandwidth(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> pd.Series:
    """Bollinger Bandwidth — (upper - lower) / middle. Low = squeeze."""
    upper, middle, lower = bollinger_bands(series, period, std_dev)
    return (upper - lower) / middle


# ═══════════════════════════════════════════════════════════════════════
# VOLUME INDICATORS
# ═══════════════════════════════════════════════════════════════════════

def vwap(df: pd.DataFrame) -> pd.Series:
    """
    Volume Weighted Average Price — the #1 institutional benchmark for India.
    Best applied to intraday data (resets each day).
    """
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (tp * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    return cumulative_tp_vol / cumulative_vol


def obv(df: pd.DataFrame) -> pd.Series:
    """
    On Balance Volume — cumulative volume based on close direction.
    Rising OBV + rising price = bullish confirmation.
    """
    direction = np.sign(df["close"].diff())
    direction.iloc[0] = 0
    return (direction * df["volume"]).cumsum()


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Money Flow Index — volume-weighted RSI."""
    tp = (df["high"] + df["low"] + df["close"]) / 3
    raw_mf = tp * df["volume"]

    positive_mf = raw_mf.where(tp > tp.shift(1), 0.0)
    negative_mf = raw_mf.where(tp < tp.shift(1), 0.0)

    positive_sum = positive_mf.rolling(window=period).sum()
    negative_sum = negative_mf.rolling(window=period).sum()

    mfr = positive_sum / negative_sum
    return 100 - (100 / (1 + mfr))


def ad_line(df: pd.DataFrame) -> pd.Series:
    """Accumulation/Distribution Line."""
    clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (df["high"] - df["low"])
    clv = clv.fillna(0)
    return (clv * df["volume"]).cumsum()


def force_index(df: pd.DataFrame, period: int = 13) -> pd.Series:
    """Force Index — price change * volume."""
    fi = df["close"].diff() * df["volume"]
    return ema(fi, period)


# ═══════════════════════════════════════════════════════════════════════
# INDIAN MARKET-SPECIFIC
# ═══════════════════════════════════════════════════════════════════════

def pivot_points(
    high: float,
    low: float,
    close: float,
) -> dict:
    """
    Standard Pivot Points — widely used by Indian traders.
    Calculated from previous day's HLC.
    Returns: PP, R1-R3, S1-S3
    """
    pp = (high + low + close) / 3
    return {
        "PP": round(pp, 2),
        "R1": round(2 * pp - low, 2),
        "R2": round(pp + (high - low), 2),
        "R3": round(high + 2 * (pp - low), 2),
        "S1": round(2 * pp - high, 2),
        "S2": round(pp - (high - low), 2),
        "S3": round(low - 2 * (high - pp), 2),
    }


def opening_range_breakout(
    df: pd.DataFrame,
    minutes: int = 15,
) -> Optional[dict]:
    """
    Opening Range Breakout (ORB) — very popular Indian intraday strategy.
    Uses first N minutes to define range, then trades breakout.

    Args:
        df: Intraday DataFrame with 'high', 'low', 'close', 'timestamp' columns.
        minutes: Opening range window (typically 15 or 30 min).

    Returns:
        Dict with 'orb_high', 'orb_low', or None.
    """
    if df.empty or len(df) < minutes:
        return None

    opening_candles = df.head(minutes)
    return {
        "orb_high": float(opening_candles["high"].max()),
        "orb_low": float(opening_candles["low"].min()),
        "orb_range": float(opening_candles["high"].max() - opening_candles["low"].min()),
    }

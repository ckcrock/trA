"""
Historical Data Manager — fetches, caches, and loads OHLCV data as Parquet files.
Reference: IMPLEMENTATION_ROADMAP.md §Phase 1, PAPER_TRADING_BACKTESTING_GUIDE.md
"""

import os
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Default catalog location (relative to project root)
DEFAULT_CATALOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "catalog",
)


class HistoricalDataManager:
    """
    Manages historical OHLCV data with local Parquet caching.

    Features:
    - Download from Angel One via AngelDataClient
    - Save/load as Parquet for fast access
    - Data quality validation (gaps, duplicates, NaN)
    - Listing of available cached datasets

    Usage:
        mgr = HistoricalDataManager()
        mgr.save(df, "SBIN", "FIVE_MINUTE")
        df = mgr.load("SBIN", "FIVE_MINUTE")
    """

    def __init__(self, catalog_dir: str = None):
        self.catalog_dir = catalog_dir or DEFAULT_CATALOG_DIR
        os.makedirs(self.catalog_dir, exist_ok=True)
        logger.info(f"📂 HistoricalDataManager initialized (catalog={self.catalog_dir})")

    # ─── File Naming ─────────────────────────────────────────────────

    def _parquet_path(self, symbol: str, interval: str) -> str:
        """Generate Parquet file path for a symbol/interval pair."""
        safe_symbol = symbol.replace("-", "_").replace("/", "_")
        filename = f"{safe_symbol}_{interval}.parquet"
        return os.path.join(self.catalog_dir, filename)

    # ─── Save / Load ─────────────────────────────────────────────────

    def save(self, df: pd.DataFrame, symbol: str, interval: str) -> str:
        """
        Save a DataFrame to Parquet.

        Args:
            df: OHLCV DataFrame (columns: timestamp/datetime, open, high, low, close, volume)
            symbol: Instrument symbol (e.g. "SBIN", "RELIANCE")
            interval: Data interval (e.g. "ONE_DAY", "FIVE_MINUTE")

        Returns:
            Path to the saved Parquet file.
        """
        if df is None or df.empty:
            raise ValueError("Cannot save empty DataFrame")

        path = self._parquet_path(symbol, interval)
        df.to_parquet(path, engine="pyarrow", index=False)
        logger.info(f"💾 Saved {len(df)} rows → {path}")
        return path

    def load(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """
        Load a cached Parquet file into a DataFrame.

        Returns:
            DataFrame or None if file doesn't exist.
        """
        path = self._parquet_path(symbol, interval)

        if not os.path.exists(path):
            logger.warning(f"⚠️ No cached data for {symbol}/{interval} at {path}")
            return None

        df = pd.read_parquet(path, engine="pyarrow")
        logger.info(f"📥 Loaded {len(df)} rows from {path}")
        return df

    # ─── Download (requires AngelDataClient) ─────────────────────────

    async def download(
        self,
        data_client,
        symbol_token: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
        symbol_name: str = None,
    ) -> Optional[pd.DataFrame]:
        """
        Download historical data via AngelDataClient and cache it as Parquet.

        Args:
            data_client: An instance of AngelDataClient (from src.adapters.angel)
            symbol_token: Angel One symbol token (e.g. "3045")
            exchange: Exchange segment ("NSE", "BSE", etc.)
            interval: Data interval ("ONE_DAY", "FIVE_MINUTE", etc.)
            from_date: Start date
            to_date: End date
            symbol_name: Human-readable symbol name for file naming (e.g. "SBIN")

        Returns:
            DataFrame with downloaded data, or None on failure.
        """
        name = symbol_name or symbol_token

        try:
            df = await data_client.get_historical_data_chunked(
                symbol_token=symbol_token,
                exchange=exchange,
                interval=interval,
                from_date=from_date,
                to_date=to_date,
            )

            if df is not None and not df.empty:
                self.save(df, name, interval)
                logger.info(f"✅ Downloaded & cached {name}/{interval}: {len(df)} rows")
                return df
            else:
                logger.warning(f"⚠️ No data returned for {name}/{interval}")
                return None

        except Exception as e:
            logger.error(f"❌ Download failed for {name}/{interval}: {e}")
            return None

    # ─── Catalog Management ──────────────────────────────────────────

    def list_available(self) -> List[Dict[str, Any]]:
        """
        List all cached datasets in the catalog directory.

        Returns:
            List of dicts with keys: symbol, interval, file, rows, size_mb, modified
        """
        datasets = []

        if not os.path.exists(self.catalog_dir):
            return datasets

        for filename in sorted(os.listdir(self.catalog_dir)):
            if not filename.endswith(".parquet"):
                continue

            filepath = os.path.join(self.catalog_dir, filename)
            stem = filename.replace(".parquet", "")

            # Parse symbol and interval from filename (e.g. "SBIN_ONE_DAY")
            # Convention: last part after the final underscore group is the interval
            # Known intervals to match against
            known_intervals = [
                "ONE_MINUTE", "THREE_MINUTE", "FIVE_MINUTE",
                "TEN_MINUTE", "FIFTEEN_MINUTE", "THIRTY_MINUTE",
                "ONE_HOUR", "ONE_DAY",
            ]

            symbol = stem
            interval = "UNKNOWN"
            for iv in known_intervals:
                if stem.endswith(f"_{iv}"):
                    symbol = stem[: -(len(iv) + 1)]
                    interval = iv
                    break

            try:
                df = pd.read_parquet(filepath, engine="pyarrow")
                row_count = len(df)
            except Exception:
                row_count = -1

            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            modified = datetime.fromtimestamp(os.path.getmtime(filepath))

            datasets.append({
                "symbol": symbol,
                "interval": interval,
                "file": filename,
                "rows": row_count,
                "size_mb": round(size_mb, 3),
                "modified": modified.isoformat(),
            })

        return datasets

    # ─── Data Quality Validation ─────────────────────────────────────

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run quality checks on a DataFrame.

        Returns:
            Dict with validation results: total_rows, duplicates, nan_count,
            gaps (for time-series), and an overall 'valid' flag.
        """
        if df is None or df.empty:
            return {"valid": False, "reason": "DataFrame is empty or None"}

        result: Dict[str, Any] = {
            "total_rows": len(df),
            "columns": list(df.columns),
        }

        # Check for duplicates
        dup_count = df.duplicated().sum()
        result["duplicates"] = int(dup_count)

        # Check for NaN values
        nan_counts = df.isnull().sum().to_dict()
        result["nan_counts"] = {k: int(v) for k, v in nan_counts.items() if v > 0}

        # Check for required OHLCV columns
        required = {"open", "high", "low", "close", "volume"}
        # Case-insensitive check
        df_cols_lower = {c.lower() for c in df.columns}
        missing_cols = required - df_cols_lower
        result["missing_columns"] = list(missing_cols)

        # Check for negative prices
        price_cols = [c for c in df.columns if c.lower() in {"open", "high", "low", "close"}]
        negative_prices = 0
        for col in price_cols:
            negative_prices += (df[col] < 0).sum()
        result["negative_prices"] = int(negative_prices)

        # Check for time-series gaps (if timestamp/datetime column exists)
        time_col = None
        for candidate in ["timestamp", "datetime", "date", "time"]:
            if candidate in df.columns:
                time_col = candidate
                break

        if time_col:
            try:
                times = pd.to_datetime(df[time_col])
                sorted_check = times.is_monotonic_increasing
                result["time_sorted"] = sorted_check
            except Exception:
                result["time_sorted"] = "unable_to_parse"

        # Overall validity
        result["valid"] = (
            dup_count == 0
            and len(result.get("nan_counts", {})) == 0
            and len(missing_cols) == 0
            and negative_prices == 0
        )

        return result

    # ─── Utility ─────────────────────────────────────────────────────

    def delete(self, symbol: str, interval: str) -> bool:
        """Delete a cached dataset."""
        path = self._parquet_path(symbol, interval)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"🗑️ Deleted {path}")
            return True
        return False

    @staticmethod
    def create_sample_data(
        symbol: str = "SAMPLE",
        days: int = 60,
        interval_minutes: int = 5,
    ) -> pd.DataFrame:
        """
        Create synthetic OHLCV data for testing.

        Generates realistic-looking price data with random walks,
        useful for testing backtesting and indicators without API access.
        """
        import numpy as np

        np.random.seed(42)

        # Trading hours per day: 9:15 AM to 3:30 PM = 375 minutes
        bars_per_day = 375 // interval_minutes
        total_bars = bars_per_day * days

        # Generate timestamps (skip weekends)
        timestamps = []
        current = datetime(2024, 1, 1, 9, 15)
        while len(timestamps) < total_bars:
            if current.weekday() < 5:  # Mon-Fri
                hour = current.hour
                minute = current.minute
                if (hour > 9 or (hour == 9 and minute >= 15)) and (
                    hour < 15 or (hour == 15 and minute <= 30)
                ):
                    timestamps.append(current)
            current += timedelta(minutes=interval_minutes)
            # Jump to next day if past market close
            if current.hour >= 16:
                current = current.replace(hour=9, minute=15) + timedelta(days=1)

        timestamps = timestamps[:total_bars]

        # Generate price series (random walk around 500)
        base_price = 500.0
        returns = np.random.normal(0, 0.002, total_bars)  # 0.2% std
        prices = base_price * np.exp(np.cumsum(returns))

        # Generate OHLCV
        opens = prices
        noise = np.random.uniform(0.995, 1.005, total_bars)
        closes = prices * noise
        highs = np.maximum(opens, closes) * np.random.uniform(1.001, 1.008, total_bars)
        lows = np.minimum(opens, closes) * np.random.uniform(0.992, 0.999, total_bars)
        volumes = np.random.randint(10000, 500000, total_bars)

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": np.round(opens, 2),
            "high": np.round(highs, 2),
            "low": np.round(lows, 2),
            "close": np.round(closes, 2),
            "volume": volumes,
        })

        return df

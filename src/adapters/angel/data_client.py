import logging
import asyncio
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
from src.adapters.angel.auth import AngelAuthManager
from src.adapters.angel.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# Known transient Angel One error codes that are safe to retry
RETRYABLE_ERROR_CODES = {"AB1004", "AB1010", "AB1000"}
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

class AngelDataClient:
    """
    Client for fetching historical data and live snapshots from Angel One.
    
    Reference: docs/angle/angel_one_complete_integration.py (AngelMarketData)
    """
    
    def __init__(self, auth_manager: AngelAuthManager, rate_limiter: TokenBucketRateLimiter):
        self.auth = auth_manager
        self.rate_limiter = rate_limiter

    def _format_dates(self, from_date: datetime, to_date: datetime, interval: str):
        """
        Format dates for the Angel One API.
        For ONE_DAY interval, align to market hours (09:15 / 15:30).
        """
        if interval == "ONE_DAY":
            from_str = from_date.strftime("%Y-%m-%d") + " 09:15"
            to_str = to_date.strftime("%Y-%m-%d") + " 15:30"
        else:
            from_str = from_date.strftime("%Y-%m-%d %H:%M")
            to_str = to_date.strftime("%Y-%m-%d %H:%M")
        return from_str, to_str

    async def get_historical_data(
        self, 
        symbol_token: str, 
        exchange: str, 
        interval: str, 
        from_date: datetime, 
        to_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical candle data with retry logic for transient errors.
        
        Args:
            symbol_token: Instrument token
            exchange: "NSE", "NFO", "BSE", "MCX"
            interval: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE,
                     FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
            from_date: Start datetime
            to_date: End datetime
            
        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        self.auth.ensure_authenticated()
        
        from_str, to_str = self._format_dates(from_date, to_date, interval)
        
        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_str,
            "todate": to_str
        }
        
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            await self.rate_limiter.acquire_async()
            
            try:
                client = self.auth.get_hist_client()
                response = client.getCandleData(params)
                
                if response and response.get('status'):
                    data = response.get('data', [])
                    
                    if not data:
                        logger.warning(f"⚠️ No historical data returned for {symbol_token}")
                        return None
                    
                    df = pd.DataFrame(
                        data,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    logger.info(f"✅ Downloaded {len(df)} candles for {symbol_token}")
                    return df
                else:
                    error_code = response.get('errorcode', '') if response else ''
                    error_msg = response.get('message', 'Unknown error') if response else 'No response'
                    last_error = f"{error_code}: {error_msg}"
                    
                    if error_code in RETRYABLE_ERROR_CODES and attempt < MAX_RETRIES:
                        delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        logger.warning(
                            f"⚠️ Retryable error {error_code} for {symbol_token} "
                            f"(attempt {attempt}/{MAX_RETRIES}). Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                        continue
                    
                    logger.warning(f"⚠️ Historical data error for {symbol_token}: {last_error}")
                    return None
                    
            except Exception as e:
                last_error = str(e)
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"⚠️ Exception fetching historical data (attempt {attempt}/{MAX_RETRIES}): "
                        f"{e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"❌ Error fetching historical data after {MAX_RETRIES} attempts: {e}")
                return None
        
        logger.error(f"❌ All {MAX_RETRIES} retry attempts failed for {symbol_token}: {last_error}")
        return None

    async def get_historical_data_chunked(
        self,
        symbol_token: str,
        exchange: str,
        interval: str,
        from_date: datetime,
        to_date: datetime,
        chunk_days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data for a large range by splitting it into chunks.
        
        Args:
            symbol_token: Instrument token
            exchange: "NSE", "NFO", "BSE", "MCX"
            interval: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE,
                     FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
            from_date: Start datetime
            to_date: End datetime
            chunk_days: Number of days per request chunk (default 30)
            
        Returns:
            DataFrame with combined results or None if all chunks fail
        """
        all_dfs = []
        current_from = from_date

        while current_from < to_date:
            current_to = min(current_from + timedelta(days=chunk_days), to_date)
            
            logger.info(f"⏳ Fetching chunk: {current_from.strftime('%Y-%m-%d')} to {current_to.strftime('%Y-%m-%d')}...")
            
            df = await self.get_historical_data(
                symbol_token=symbol_token,
                exchange=exchange,
                interval=interval,
                from_date=current_from,
                to_date=current_to
            )
            
            if df is not None and not df.empty:
                all_dfs.append(df)
            
            # Move to next chunk (overlapping by 1 second to ensure no gaps if needed, 
            # though Angel One dates are usually inclusive)
            current_from = current_to

        if not all_dfs:
            return None

        # Combine, sort, and deduplicate
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df.drop_duplicates(subset=['timestamp'], keep='first', inplace=True)
        combined_df.sort_values('timestamp', inplace=True)
        
        logger.info(f"✅ Chunked fetch complete: {len(combined_df)} total bars collected.")
        return combined_df

    async def get_ltp(self, exchange: str, symbol_token: str, trading_symbol: str = None) -> Optional[float]:
        """
        Get Last Traded Price.
        
        Args:
            exchange: NSE, BSE, NFO, MCX
            symbol_token: Instrument token
            trading_symbol: Trading symbol (optional)
        
        Returns:
            Last traded price or None
        """
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.ltpData(exchange, trading_symbol, symbol_token)
            
            if response and response.get('status'):
                data = response.get('data', {})
                return float(data.get('ltp', 0))
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching LTP: {e}")
            return None

    async def get_quote(self, exchange: str, symbol_token: str) -> Optional[Dict]:
        """
        Get full quote with bid/ask and market depth.
        Uses getMarketData with mode="FULL".
        """
        self.auth.ensure_authenticated()
        await self.rate_limiter.acquire_async()
        
        try:
            client = self.auth.get_smart_api_client()
            response = client.getMarketData(
                mode="FULL",
                exchangeTokens={exchange: [symbol_token]}
            )
            
            if response and response.get('status'):
                data = response.get('data', {}).get('fetched', [])
                if data:
                    return data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching quote: {e}")
            return None

    async def get_intraday_data(
        self,
        symbol_token: str,
        exchange: str = "NSE",
        interval: str = "FIVE_MINUTE"
    ) -> Optional[pd.DataFrame]:
        """Get today's intraday data (convenience method)."""
        today = datetime.now()
        from_date = today.replace(hour=9, minute=15, second=0)
        to_date = today
        
        return await self.get_historical_data(
            exchange=exchange,
            symbol_token=symbol_token,
            interval=interval,
            from_date=from_date,
            to_date=to_date
        )

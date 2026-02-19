import pandas as pd
import requests
import json
import logging
import os
import glob
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class SymbolResolver:
    """
    Manages instrument catalog and symbol resolution.
    Downloads and caches Angel One scrip master.
    """
    
    SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    
    def __init__(self, cache_dir: str = "data/catalog/"):
        self.cache_dir = cache_dir
        self.instruments_df: Optional[pd.DataFrame] = None
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def download_scrip_master(self) -> pd.DataFrame:
        """
        Download latest scrip master from Angel One
        """
        logger.info("Downloading Angel One scrip master...")
        
        try:
            response = requests.get(self.SCRIP_MASTER_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data)
            
            # Type conversion and optimization
            df['expiry'] = pd.to_datetime(df['expiry'], errors='coerce')
            df['token'] = df['token'].astype(str)
            
            # Save to cache
            filename = os.path.join(self.cache_dir, f"angel_scrip_master_{datetime.now().strftime('%Y%m%d')}.csv")
            df.to_csv(filename, index=False)
            
            logger.info(f"✅ Downloaded {len(df)} instruments")
            logger.info(f"Saved to: {filename}")
            
            self.instruments_df = df
            return df
            
        except Exception as e:
            logger.error(f"❌ Error downloading scrip master: {e}")
            raise

    def load_instruments(self):
        """Load instruments from cache or download if missing"""
        pattern = os.path.join(self.cache_dir, "angel_scrip_master_*.csv")
        files = glob.glob(pattern)
        
        if not files:
            logger.warning("No cached scrip master found. Downloading...")
            self.download_scrip_master()
            return

        # Get most recent file
        latest_file = max(files, key=os.path.getctime)
        logger.info(f"Loading cached scrip master: {latest_file}")
        
        # Optimization: Use pyarrow engine if available, or specify dtypes
        self.instruments_df = pd.read_csv(latest_file, dtype={'token': str})
        self.instruments_df['expiry'] = pd.to_datetime(self.instruments_df['expiry'], errors='coerce')
        
    def resolve_by_symbol(self, symbol: str, exchange: str = 'NSE') -> Optional[Dict]:
        """
        Find instrument by symbol (e.g., 'SBIN-EQ', 'NIFTY')
        """
        if self.instruments_df is None:
            self.load_instruments()
            
        # Case insensitive search
        mask = (
            (self.instruments_df['symbol'] == symbol) & 
            (self.instruments_df['exch_seg'] == exchange)
        )
        result = self.instruments_df[mask]
        
        if result.empty:
            # Try partial match or alternate formatting if needed
            return None
            
        return result.iloc[0].to_dict()

    def resolve_by_token(self, token: str, exchange: str = 'NSE') -> Optional[Dict]:
        """Find instrument by token"""
        if self.instruments_df is None:
            self.load_instruments()
            
        mask = (
            (self.instruments_df['token'] == token) & 
            (self.instruments_df['exch_seg'] == exchange)
        )
        result = self.instruments_df[mask]
        
        if result.empty:
            return None
            
        return result.iloc[0].to_dict()

    def get_liquid_stocks(self, min_volume: int = 1000000) -> List[Dict]:
        """Get list of liquid stocks (example implementation)"""
        # This is basic; real implementation would filter by volume
        if self.instruments_df is None:
            self.load_instruments()
            
        # Return top 50 Nifty stocks for now
        # logic placeholder
        return []

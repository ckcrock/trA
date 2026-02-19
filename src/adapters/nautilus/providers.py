"""
Instrument Provider for Angel One Nautilus Adapter.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from src.catalog.symbol_resolver import SymbolResolver

try:
    from nautilus_trader.common.providers import InstrumentProvider
    from nautilus_trader.model.instruments import Instrument, Equity
    from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
    from nautilus_trader.model.objects import Price, Quantity, Currency
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy class
    class InstrumentProvider: pass
    class Instrument: pass

logger = logging.getLogger(__name__)


@dataclass
class BrokerInstrumentRef:
    """
    Lightweight instrument reference used by adapter bridge paths.
    Works even when full Nautilus instrument construction fails.
    """

    instrument_id: str
    raw_symbol: str
    broker_symbol_token: str
    venue: Any


if NAUTILUS_AVAILABLE:
    class AngelOneInstrumentProvider(InstrumentProvider):
        """
        Provides Angel One instruments to Nautilus Trader.
        Uses src.catalog.symbol_resolver.SymbolResolver as the backend.
        """
        
        def __init__(self, symbol_resolver: SymbolResolver):
            super().__init__()
            self.resolver = symbol_resolver
            self._cache: Dict[str, Any] = {}
            self._token_cache: Dict[str, BrokerInstrumentRef] = {}
            self._instrument_tokens: Dict[str, str] = {}
            
        def load_all(self, filters: Dict = None):
            """Load all instruments (expensive operation)."""
            if not self.resolver.instruments_df:
                self.resolver.load_instruments()
                
            # Convert DF to Nautilus instruments
            # This could be massive (80k+ symbols), so we might want to lazy load
            # or filter strictly.
            pass

        def find(self, instrument_id: str) -> Optional[Instrument]:
            """Find instrument by ID (e.g. 'SBIN-EQ.NSE')."""
            if instrument_id in self._cache:
                return self._cache[instrument_id]
                
            # Parse ID
            try:
                # Expected format: SYMBOL-SERIES.VENUE or SYMBOL.VENUE
                parts = instrument_id.split('.')
                if len(parts) != 2:
                    return None
                    
                symbol_part = parts[0]
                venue_part = parts[1]
                
                # Try to resolve
                info = self.resolver.resolve_by_symbol(symbol_part, venue_part)
                if not info:
                    return None

                broker_ref = BrokerInstrumentRef(
                    instrument_id=instrument_id,
                    raw_symbol=str(info.get("symbol", symbol_part)),
                    broker_symbol_token=str(info.get("token", "")),
                    venue=Venue(venue_part),
                )
                self._instrument_tokens[instrument_id] = broker_ref.broker_symbol_token
                self._token_cache[broker_ref.broker_symbol_token] = broker_ref
                    
                # Create Instrument
                instrument = self._create_instrument(info, instrument_id)
                if instrument is not None:
                    self._cache[instrument_id] = instrument
                    return instrument

                # Fallback to lightweight bridge object.
                self._cache[instrument_id] = broker_ref
                return broker_ref
                
            except Exception as e:
                logger.error(f"Error finding instrument {instrument_id}: {e}")
                return None

        def get_broker_token(self, instrument_id: str) -> Optional[str]:
            token = self._instrument_tokens.get(str(instrument_id))
            return token if token else None

        def find_by_token(self, token: str) -> Optional[BrokerInstrumentRef]:
            """
            Resolve instrument reference by broker token for WS tick translation.
            """
            key = str(token)
            cached = self._token_cache.get(key)
            if cached:
                return cached

            info = self.resolver.resolve_by_token(key)
            if not info:
                return None

            symbol = str(info.get("symbol", "")).strip()
            exch = str(info.get("exch_seg", "NSE")).strip().upper()
            instrument_id = f"{symbol}.{exch}" if symbol else f"{key}.{exch}"

            ref = BrokerInstrumentRef(
                instrument_id=instrument_id,
                raw_symbol=symbol or instrument_id,
                broker_symbol_token=key,
                venue=Venue(exch),
            )
            self._token_cache[key] = ref
            return ref

        def _create_instrument(self, info: Dict, instrument_id: str) -> Instrument:
            """Create Nautilus Instrument from Angel One info dict."""
            try:
                # Basic mapping
                symbol = Symbol(info['symbol'])
                # Keep live adapter robust for symbol coverage by defaulting to Equity
                # when a full derivative instrument mapping is unavailable.
                price_increment = self._to_price_increment(info.get("tick_size", "0.05"))
                return Equity(
                    instrument_id=InstrumentId.from_str(instrument_id),
                    raw_symbol=symbol,
                    currency=Currency.from_str("INR"),
                    price_precision=self._price_precision(price_increment),
                    price_increment=price_increment,
                    lot_size=Quantity.from_str(str(info.get('lotsize', '1'))),
                    ts_event=0,
                    ts_init=0
                )

            except Exception as e:
                logger.error(f"Error creating instrument: {e}")
                return None

        @staticmethod
        def _to_price_increment(raw: Any) -> Price:
            try:
                value = float(raw)
            except (TypeError, ValueError):
                value = 0.05
            if value >= 1:
                value = value / 100.0
            if value <= 0:
                value = 0.05
            return Price.from_str(f"{value:.4f}".rstrip("0").rstrip("."))

        @staticmethod
        def _price_precision(price_increment: Price) -> int:
            precision = getattr(price_increment, "precision", None)
            if isinstance(precision, int):
                return precision
            return 2

else:
    class AngelOneInstrumentProvider:
        """Dummy provider when Nautilus is missing."""
        def __init__(self, *args, **kwargs): pass

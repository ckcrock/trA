"""
Instrument Provider for Angel One Nautilus Adapter.
"""

import logging
from typing import Dict, List, Optional
from src.catalog.symbol_resolver import SymbolResolver

try:
    from nautilus_trader.common.providers import InstrumentProvider
    from nautilus_trader.model.instruments import Instrument, Equity, Future, Option, Currency
    from nautilus_trader.model.identifiers import InstrumentId, Venue, Symbol
    from nautilus_trader.model.objects import Price, Quantity
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy class
    class InstrumentProvider: pass
    class Instrument: pass

logger = logging.getLogger(__name__)


if NAUTILUS_AVAILABLE:
    class AngelOneInstrumentProvider(InstrumentProvider):
        """
        Provides Angel One instruments to Nautilus Trader.
        Uses src.catalog.symbol_resolver.SymbolResolver as the backend.
        """
        
        def __init__(self, symbol_resolver: SymbolResolver):
            self.resolver = symbol_resolver
            self._cache: Dict[str, Instrument] = {}
            
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
                    
                # Create Instrument
                instrument = self._create_instrument(info, instrument_id)
                if instrument:
                    self._cache[instrument_id] = instrument
                return instrument
                
            except Exception as e:
                logger.error(f"Error finding instrument {instrument_id}: {e}")
                return None

        def _create_instrument(self, info: Dict, instrument_id: str) -> Instrument:
            """Create Nautilus Instrument from Angel One info dict."""
            try:
                # Basic mapping
                symbol = Symbol(info['symbol'])
                venue = Venue("ANGELONE")
                
                # Determine type
                inst_type = info.get('instrumenttype', '')
                
                if inst_type.startswith("OPT"):
                    return Option(
                        instrument_id=InstrumentId(instrument_id),
                        raw_symbol=symbol,
                        venue=venue,
                        step_price=Price.from_str(str(info.get('tick_size', '0.05'))),
                        step_size=Quantity.from_str(str(info.get('lotsize', '1'))),
                        product_class="OPTION",
                        # ... other usage fields
                        base_currency=Currency.from_str("INR"),
                        quote_currency=Currency.from_str("INR"),
                        lot_size=Quantity.from_str(str(info.get('lotsize', '1'))),
                        underlying=Symbol(info.get('name', '')),
                        activation_ns=0,  # TODO parse expiry
                        expiration_ns=0,  # TODO parse expiry
                        strike_price=Price.from_str(str(info.get('strike', '0'))),
                        option_type="CALL" if inst_type.endswith("CE") else "PUT",
                        ts_event=0,
                        ts_init=0
                    )
                else:
                    # Default to Equity
                    return Equity(
                        instrument_id=InstrumentId(instrument_id),
                        raw_symbol=symbol,
                        currency=Currency.from_str("INR"),
                        price_precision=2,
                        price_increment=Price.from_str(str(info.get('tick_size', '0.05'))),
                        lot_size=Quantity.from_str(str(info.get('lotsize', '1'))),
                        ts_event=0,
                        ts_init=0
                    )

            except Exception as e:
                logger.error(f"Error creating instrument: {e}")
                return None

else:
    class AngelOneInstrumentProvider:
        """Dummy provider when Nautilus is missing."""
        def __init__(self, *args, **kwargs): pass

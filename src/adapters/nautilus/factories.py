"""
Factories for Angel One Nautilus Adapter.
"""

from typing import Optional

try:
    from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory
    from nautilus_trader.common.component import MessageBus, Clock
    from nautilus_trader.cache.cache import Cache
    from nautilus_trader.common.logging import Logger
    from nautilus_trader.config import LiveDataClientConfig, LiveExecClientConfig
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes
    class LiveDataClientFactory: pass
    class LiveExecClientFactory: pass

from .data import AngelOneDataClient
from .execution import AngelOneExecutionClient
from .providers import AngelOneInstrumentProvider
from .config import AngelOneDataClientConfig, AngelOneExecClientConfig

# Import dependency functions to get singletons
from src.api.dependencies import get_data_client, get_execution_client, get_ws_client, get_symbol_resolver

if NAUTILUS_AVAILABLE:
    class AngelOneDataClientFactory(LiveDataClientFactory):
        """Factory for Angel One Data Client."""
        
        def create(
            self,
            loop,
            msgbus: MessageBus,
            cache: Cache,
            clock: Clock,
            logger: Logger,
            config: AngelOneDataClientConfig,
        ) -> AngelOneDataClient:
            
            # Use existing singletons
            client = get_data_client()
            ws_client = get_ws_client()
            
            # Create provider using existing resolver
            resolver = get_symbol_resolver()
            provider = AngelOneInstrumentProvider(resolver)
            
            return AngelOneDataClient(
                loop=loop,
                client=client,
                ws_client=ws_client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                logger=logger,
                instrument_provider=provider,
                config=config,
            )

    class AngelOneExecClientFactory(LiveExecClientFactory):
        """Factory for Angel One Execution Client."""
        
        def create(
            self,
            loop,
            msgbus: MessageBus,
            cache: Cache,
            clock: Clock,
            logger: Logger,
            config: AngelOneExecClientConfig,
        ) -> AngelOneExecutionClient:
            
            # Use existing singletons
            client = get_execution_client()
            
            # Create provider
            resolver = get_symbol_resolver()
            provider = AngelOneInstrumentProvider(resolver)
            
            return AngelOneExecutionClient(
                loop=loop,
                client=client,
                msgbus=msgbus,
                cache=cache,
                clock=clock,
                logger=logger,
                instrument_provider=provider,
                config=config,
            )
else:
    class AngelOneDataClientFactory: pass
    class AngelOneExecClientFactory: pass

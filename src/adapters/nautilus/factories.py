"""
Factories for Angel One Nautilus Adapter.
"""

from typing import Optional, Any

try:
    from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes
    class LiveDataClientFactory: pass
    class LiveExecClientFactory: pass

MessageBus = Any
Clock = Any
Cache = Any
Logger = Any

from .data import AngelOneDataClient
from .execution import AngelOneExecutionClient
from .providers import AngelOneInstrumentProvider
from .config import AngelOneDataClientConfig, AngelOneExecClientConfig

# Import dependency functions to get singletons
from src.api.dependencies import get_data_client, get_execution_client, get_ws_client, get_symbol_resolver

if NAUTILUS_AVAILABLE:
    class AngelOneDataClientFactory(LiveDataClientFactory):
        """Factory for Angel One Data Client."""

        @classmethod
        def create(cls, *args, **kwargs) -> AngelOneDataClient:
            """
            Supports multiple Nautilus factory signatures across versions.
            """
            loop = kwargs.get("loop") or (args[0] if len(args) > 0 else None)
            # New signature: (loop, name, config, msgbus, cache, clock)
            config = kwargs.get("config") or (args[2] if len(args) > 2 else AngelOneDataClientConfig())
            msgbus = kwargs.get("msgbus") or (args[3] if len(args) > 3 else None)
            cache = kwargs.get("cache") or (args[4] if len(args) > 4 else None)
            clock = kwargs.get("clock") or (args[5] if len(args) > 5 else None)
            
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
                instrument_provider=provider,
                config=config,
            )

    class AngelOneExecClientFactory(LiveExecClientFactory):
        """Factory for Angel One Execution Client."""

        @classmethod
        def create(cls, *args, **kwargs) -> AngelOneExecutionClient:
            """
            Supports multiple Nautilus factory signatures across versions.
            """
            loop = kwargs.get("loop") or (args[0] if len(args) > 0 else None)
            # New signature: (loop, name, config, msgbus, cache, clock)
            config = kwargs.get("config") or (args[2] if len(args) > 2 else AngelOneExecClientConfig())
            msgbus = kwargs.get("msgbus") or (args[3] if len(args) > 3 else None)
            cache = kwargs.get("cache") or (args[4] if len(args) > 4 else None)
            clock = kwargs.get("clock") or (args[5] if len(args) > 5 else None)
            
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
                instrument_provider=provider,
                config=config,
            )
else:
    class AngelOneDataClientFactory: pass
    class AngelOneExecClientFactory: pass

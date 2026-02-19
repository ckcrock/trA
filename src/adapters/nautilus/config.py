"""
Configuration classes for Angel One Nautilus Adapter.
"""

from typing import Optional
import os

try:
    from nautilus_trader.config import LiveDataClientConfig, LiveExecClientConfig
    from pydantic import Field, SecretStr
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Dummy classes
    class LiveDataClientConfig: pass
    class LiveExecClientConfig: pass
    from pydantic import Field, SecretStr


if NAUTILUS_AVAILABLE:
    class AngelOneDataClientConfig(LiveDataClientConfig):
        """Configuration for Angel One Data Client."""
        
        api_key: str = Field(default_factory=lambda: os.getenv("ANGEL_API_KEY", ""), description="Angel One API Key")
        client_code: str = Field(default_factory=lambda: os.getenv("ANGEL_CLIENT_CODE", ""), description="Client Code")
        password: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ANGEL_PASSWORD", "")), description="MPIN/Password")
        totp_secret: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ANGEL_TOTP_SECRET", "")), description="TOTP Secret")
        
        # Data specific
        history_api_key: str = Field(default_factory=lambda: os.getenv("ANGEL_HIST_API_KEY", ""), description="Historical API Key")
        
        instrument_provider_timeout: float = 60.0


    class AngelOneExecClientConfig(LiveExecClientConfig):
        """Configuration for Angel One Execution Client."""
        
        api_key: str = Field(default_factory=lambda: os.getenv("ANGEL_API_KEY", ""), description="Angel One API Key")
        client_code: str = Field(default_factory=lambda: os.getenv("ANGEL_CLIENT_CODE", ""), description="Client Code")
        password: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ANGEL_PASSWORD", "")), description="MPIN/Password")
        totp_secret: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ANGEL_TOTP_SECRET", "")), description="TOTP Secret")
        
        # Execution specific
        account_id: Optional[str] = None
        reconciliation_interval_secs: float = 60.0

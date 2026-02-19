"""
Configuration classes for Angel One Nautilus adapter.
"""

import os

try:
    from nautilus_trader.config import LiveDataClientConfig, LiveExecClientConfig
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False

    class LiveDataClientConfig:  # pragma: no cover
        pass

    class LiveExecClientConfig:  # pragma: no cover
        pass


if NAUTILUS_AVAILABLE:
    class AngelOneDataClientConfig(LiveDataClientConfig, frozen=True):
        """Configuration for Angel One live data client."""

        api_key: str | None = os.getenv("ANGEL_API_KEY") or None
        client_code: str | None = os.getenv("ANGEL_CLIENT_CODE") or None
        password: str | None = os.getenv("ANGEL_PASSWORD") or None
        totp_secret: str | None = os.getenv("ANGEL_TOTP_SECRET") or None
        history_api_key: str | None = os.getenv("ANGEL_HIST_API_KEY") or None
        instrument_provider_timeout: float = 60.0


    class AngelOneExecClientConfig(LiveExecClientConfig, frozen=True):
        """Configuration for Angel One live execution client."""

        api_key: str | None = os.getenv("ANGEL_API_KEY") or None
        client_code: str | None = os.getenv("ANGEL_CLIENT_CODE") or None
        password: str | None = os.getenv("ANGEL_PASSWORD") or None
        totp_secret: str | None = os.getenv("ANGEL_TOTP_SECRET") or None
        account_id: str | None = None
        reconciliation_interval_secs: float = 60.0
else:
    class AngelOneDataClientConfig(LiveDataClientConfig):  # pragma: no cover
        pass

    class AngelOneExecClientConfig(LiveExecClientConfig):  # pragma: no cover
        pass

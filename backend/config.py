import os
from dataclasses import dataclass


@dataclass
class Settings:
    # Bot
    BOT_NAME: str = "DOUBLE-A TRADER"
    MIN_TRADE: float = 1.0

    # License
    LICENSE_KEY: str = "20892089"

    # API
    API_URL: str = os.getenv("API_URL", "")
    API_KEY: str = os.getenv("API_KEY", "")

    # Trading
    DEFAULT_TIMEFRAME: int = 60
    DEFAULT_PAYOUT: float = 0.80

    # Market
    MARKET_MODE: str = "LIVE"

    # Timezone
    TIMEZONE: str = "UTC"

    # Safety
    MAX_TRADES_PER_SIGNAL: int = 1
    MARTINGALE_ENABLED: bool = False


settings = Settings()

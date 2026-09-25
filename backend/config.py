import os
from dataclasses import dataclass


@dataclass
class Settings:
    # =========================
    # BOT
    # =========================
    BOT_NAME: str = "DOUBLE-A TRADER"

    # Minimum trade amount
    MIN_TRADE: float = 1.0

    # =========================
    # LICENSE
    # =========================
    LICENSE_KEY: str = "20892089"

    # =========================
    # MARKET SELECTORS
    # =========================
    # Dono ko independently ON/OFF kiya ja sakta hai.
    LIVE_ENABLED: bool = True
    OTC_ENABLED: bool = False

    # Saturday / Sunday scanner OFF
    WEEKEND_OFF: bool = True

    # =========================
    # SIGNAL
    # =========================
    TIMEFRAME_SECONDS: int = 60
    EXPIRY_MINUTES: int = 1

    # Minimum confidence required
    MIN_SIGNAL_SCORE: float = 75.0

    # =========================
    # MONEY MANAGEMENT
    # =========================
    # Default: Non-MTG
    MARTINGALE_ENABLED: bool = False

    # Maximum one-step recovery
    MAX_MTG_STEPS: int = 1

    # =========================
    # TIME
    # =========================
    TIMEZONE: str = "UTC"

    # =========================
    # API
    # =========================
    API_URL: str = os.getenv("API_URL", "")
    API_KEY: str = os.getenv("API_KEY", "")

    # Quotex credentials environment variables
    QUOTEX_EMAIL: str = os.getenv("QUOTEX_EMAIL", "")
    QUOTEX_PASSWORD: str = os.getenv("QUOTEX_PASSWORD", "")


settings = Settings()

# scanner.py

import asyncio
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any

from strategy import Candle, StrategyEngine


# ============================================================
# SIGNAL MODEL
# ============================================================

@dataclass
class FutureSignal:

    pair: str
    market: str

    direction: str

    score: float
    confidence: str
    status: str

    signal_time: int

    expiry_minutes: int = 1

    support: float = 0.0
    resistance: float = 0.0

    reasons: List[str] = field(default_factory=list)

    # Multi timeframe
    trend_1m: str = "UNKNOWN"
    trend_5m: str = "UNKNOWN"
    trend_15m: str = "UNKNOWN"

    # Signal quality
    momentum: str = "UNKNOWN"
    volatility: float = 0.0

    # Lifecycle
    last_update: int = 0
    expires_at: int = 0

    # Result
    result: str = "PENDING"

    # Number of times the setup was reconfirmed
    confirmations: int = 0

    def to_dict(self):
        return asdict(self)


# ============================================================
# MARKET SCANNER
# ============================================================

class MarketScanner:

    def __init__(
        self,
        api_client=None,

        future_score: float = 55.0,
        monitor_score: float = 65.0,
        confirmed_score: float = 75.0,

        signal_ttl_seconds: int = 180,

        max_future_signals: int = 50,

        rescan_interval: int = 10,
    ):

        self.api_client = api_client

        self.strategy = StrategyEngine(
            future_score=future_score,
            monitor_score=monitor_score,
            confirmed_score=confirmed_score,
        )

        # ====================================================
        # MARKET SWITCHES
        # ====================================================

        self.live_enabled = True
        self.otc_enabled = True

        # ====================================================
        # SIGNAL SETTINGS
        # ====================================================

        self.signal_ttl_seconds = signal_ttl_seconds

        self.max_future_signals = max_future_signals

        self.rescan_interval = rescan_interval

        # ====================================================
        # ACTIVE SIGNALS
        # ====================================================

        self.future_signals: Dict[
            str,
            FutureSignal
        ] = {}

        # ====================================================
        # HISTORY
        # ====================================================

        self.history: List[
            FutureSignal
        ] = []

        # ====================================================
        # STATE
        # ====================================================

        self.running = False

        self.last_scan = 0

        self.scan_count = 0

    # ========================================================
    # MARKET CONTROL
    # ========================================================

    def set_live_enabled(
        self,
        enabled: bool,
    ):

        self.live_enabled = bool(
            enabled
        )

    def set_otc_enabled(
        self,
        enabled: bool,
    ):

        self.otc_enabled = bool(
            enabled
        )

    # ========================================================
    # KEY
   

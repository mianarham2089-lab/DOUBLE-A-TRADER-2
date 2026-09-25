# backend/scanner.py

import asyncio
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

from strategy import StrategyEngine
from market_data import QuotexMarketData


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

    reasons: List[str] = field(
        default_factory=list
    )

    trend_1m: str = "UNKNOWN"
    trend_5m: str = "UNKNOWN"
    trend_15m: str = "UNKNOWN"

    momentum: str = "UNKNOWN"
    volatility: float = 0.0

    last_update: int = 0
    expires_at: int = 0

    result: str = "PENDING"

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

        self.api_client = (
            api_client
            or QuotexMarketData()
        )

        self.strategy = StrategyEngine(
            future_score=future_score,
            monitor_score=monitor_score,
            confirmed_score=confirmed_score,
        )

        self.signal_ttl_seconds = (
            signal_ttl_seconds
        )

        self.max_future_signals = (
            max_future_signals
        )

        self.rescan_interval = (
            rescan_interval
        )

        self.future_signals: Dict[
            str, FutureSignal
        ] = {}

        self.history: List[
            FutureSignal
        ] = []

        self.running = False

        self.last_scan = 0

        self.scan_count = 0

        self.live_enabled = True
        self.otc_enabled = True

        self._task = None

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
    # MARKET TYPE
    # ========================================================

    @staticmethod
    def market_type(symbol: str) -> str:

        if symbol.lower().endswith(
            "_otc"
        ):
            return "OTC"

        return "LIVE"

    # ========================================================
    # PAIR FILTER
    # ========================================================

    def allowed_pair(
        self,
        symbol: str,
    ) -> bool:

        market = self.market_type(
            symbol
        )

        if market == "LIVE":
            return self.live_enabled

        if market == "OTC":
            return self.otc_enabled

        return False

    # ========================================================
    # NORMALIZE MARKET RESPONSE
    # ========================================================

    @staticmethod
    def extract_symbols(
        data
    ) -> List[str]:

        if not data:
            return []

        if isinstance(data, list):

            result = []

            for item in data:

                if isinstance(item, str):
                    result.append(item)

                elif isinstance(item, dict):

                    symbol = (
                        item.get("symbol")
                        or item.get("pair")
                        or item.get("name")
                    )

                    if symbol:
                        result.append(
                            str(symbol)
                        )

            return result

        if isinstance(data, dict):

            for key in (
                "data",
                "markets",
                "assets",
                "symbols",
                "pairs",
            ):

                if key in data:

                    return (
                        MarketScanner
                        .extract_symbols(
                            data[key]
                        )
                    )

        return []

    # ========================================================
    # GET PAIRS
    # ========================================================

    def get_pairs(self) -> List[str]:

        try:

            markets = (
                self.api_client
                .get_markets()
            )

            symbols = (
                self.extract_symbols(
                    markets
                )
            )

            return [
                symbol
                for symbol in symbols
                if self.allowed_pair(
                    symbol
                )
            ]

        except Exception as error:

            print(
                "Market list error:",
                error
            )

            return []

    # ========================================================
    # TREND FROM CANDLES
    # ========================================================

    def get_trend(
        self,
        candles,
    ) -> str:

        try:

            return self.strategy.trend(
                candles
            )

        except Exception:

            return "UNKNOWN"

    # ========================================================
    # CREATE SIGNAL
    # ========================================================

    def create_signal(
        self,
        pair: str,
        candles_1m,
        candles_5m=None,
        candles_15m=None,
    ) -> Optional[FutureSignal]:

        if len(candles_1m) < 20:
            return None

        higher = (
            candles_5m
            if candles_5m
            else None
        )

        analysis = (
            self.strategy.analyze(
                candles_1m,
                higher
            )
        )

        if not analysis.direction:
            return None

        now = int(
            time.time()
        )

        market = (
            self.market_type(pair)
        )

        trend_1m = self.get_trend(
            candles_1m
        )

        trend_5m = (
            self.get_trend(
                candles_5m
            )
            if candles_5m
            else "UNKNOWN"
        )

        trend_15m = (
            self.get_trend(
                candles_15m
            )
            if candles_15m
            else "UNKNOWN"
        )

        atr = analysis.indicators.get(
            "atr",
            0.0
        )

        signal = FutureSignal(

            pair=pair,

            market=market,

            direction=(
                analysis.direction
            ),

            score=float(
                analysis.score
            ),

            confidence=(
                analysis.confidence
            ),

            status=(
                analysis.status
            ),

            signal_time=now,

            expiry_minutes=1,

            support=float(
                analysis.support
            ),

            resistance=float(
                analysis.resistance
            ),

            reasons=list(
                analysis.reasons
            ),

            trend_1m=trend_1m,

            trend_5m=trend_5m,

            trend_15m=trend_15m,

            momentum=(
                "UP"
                if analysis.direction
                == "CALL"
                else "DOWN"
            ),

            volatility=float(
                atr
            ),

            last_update=now,

            expires_at=(
                now
                + self.signal_ttl_seconds
            ),

            result="PENDING",

            confirmations=1,
        )

        return signal

    # ========================================================
    # SCAN ONE PAIR
    # ========================================================

    def scan_pair(
        self,
        pair: str,
    ) -> Optional[FutureSignal]:

        try:

            candles_1m = (
                self.api_client
                .get_candles(
                    pair,
                    interval="1m",
                    limit=100,
                )
            )

            if len(candles_1m) < 20:
                return None

            candles_5m = (
                self.api_client
                .get_candles(
                    pair,
                    interval="5m",
                    limit=100,
                )
            )

            candles_15m = (
                self.api_client
                .get_candles(
                    pair,
                    interval="15m",
                    limit=100,
                )
            )

            return self.create_signal(
                pair,
                candles_1m,
                candles_5m,
                candles_15m,
            )

        except Exception as error:

            print(
                f"Scan error {pair}:",
                error
            )

            return None

    # ========================================================
    # STORE SIGNAL
    # ========================================================

    def store_signal(
        self,
        signal: FutureSignal,
    ):

        key = (
            f"{signal.market}:"
            f"{signal.pair}"
        )

        old = (
            self.future_signals
            .get(key)
        )

        if old:

            signal.confirmations = (
                old.confirmations + 1
            )

        self.future_signals[key] = (
            signal
        )

        # Keep history
        self.history.insert(
            0,
            signal
        )

        # Limit history
        if len(self.history) > 500:
            self.history = (
                self.history[:500]
            )

    # ========================================================
    # REMOVE EXPIRED SIGNALS
    # ========================================================

    def cleanup_expired(self):

        now = int(
            time.time()
        )

        expired = []

        for key, signal in (
            self.future_signals.items()
        ):

            if (
                signal.expires_at
                and now > signal.expires_at
            ):

                expired.append(key)

        for key in expired:

            del self.future_signals[
                key
            ]

    # ========================================================
    # SCAN ALL
    # ========================================================

    def scan_once(self):

        pairs = self.get_pairs()

        self.scan_count += 1

        self.last_scan = int(
            time.time()
        )

        if not pairs:
            return

        for pair in pairs:

            signal = self.scan_pair(
                pair
            )

            if signal:

                self.store_signal(
                    signal
                )

            # Prevent one bad pair from
            # stopping the entire scanner.
            continue

        self.cleanup_expired()

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    async def run(self):

        self.running = True

        while self.running:

            try:

                await asyncio.to_thread(
                    self.scan_once
                )

            except Exception as error:

                print(
                    "Scanner loop error:",
                    error
                )

            await asyncio.sleep(
                self.rescan_interval
            )

    # ========================================================
    # START
    # ========================================================

    def start_background(self):

        if self.running:
            return

        try:

            loop = asyncio.get_running_loop()

        except RuntimeError:

            raise RuntimeError(
                "Scanner must be started "
                "inside an active event loop"
            )

        self._task = (
            loop.create_task(
                self.run()
            )
        )

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self):

        self.running = False

        if self._task:

            try:

                await self._task

            except asyncio.CancelledError:

                pass

            self._task = None

    # ========================================================
    # FUTURE SIGNALS
    # ========================================================

    def get_future_signals(
        self,
        market: Optional[str] = None,
    ):

        self.cleanup_expired()

        signals = list(
            self.future_signals.values()
        )

        if market:

            market = market.upper()

            signals = [
                signal
                for signal in signals
                if signal.market
                == market
            ]

        signals.sort(
            key=lambda signal:
                signal.score,
            reverse=True,
        )

        return [
            signal.to_dict()
            for signal in signals[
                :self.max_future_signals
            ]
        ]

    # ========================================================
    # CONFIRMED SIGNALS
    # ========================================================

    def get_confirmed_signals(
        self,
        market: Optional[str] = None,
    ):

        signals = [
            signal
            for signal in self.history
            if signal.status
            == "CONFIRMED"
        ]

        if market:

            market = market.upper()

            signals = [
                signal
                for signal in signals
                if signal.market
                == market
            ]

        return [
            signal.to_dict()
            for signal in signals[:100]
        ]

    # ========================================================
    # STATISTICS
    # ========================================================

    def get_statistics(self):

        completed = [
            signal
            for signal in self.history
            if signal.result
            in ("WIN", "LOSS")
        ]

        wins = sum(
            1
            for signal in completed
            if signal.result == "WIN"
        )

        losses = sum(
            1
            for signal in completed
            if signal.result == "LOSS"
        )

        total = len(completed)

        accuracy = (
            round(
                wins / total * 100,
                2,
            )
            if total
            else 0.0
        )

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "accuracy": accuracy,
        }

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

        return {
            "running": self.running,
            "live_enabled":
                self.live_enabled,
            "otc_enabled":
                self.otc_enabled,
            "active_signals":
                len(
                    self.future_signals
                ),
            "scan_count":
                self.scan_count,
            "last_scan":
                self.last_scan,
            "data_api":
                self.api_client.status(),
        }

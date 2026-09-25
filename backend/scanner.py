# backend/scanner.py

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

        self.api_client = api_client

        self.strategy = StrategyEngine(
            future_score=future_score,
            monitor_score=monitor_score,
            confirmed_score=confirmed_score,
        )

        # ====================================================
        # MARKET TYPES
        # ====================================================

        self.live_enabled = True
        self.otc_enabled = True

        # ====================================================
        # SETTINGS
        # ====================================================

        self.signal_ttl_seconds = signal_ttl_seconds
        self.max_future_signals = max_future_signals
        self.rescan_interval = rescan_interval

        # ====================================================
        # SIGNAL STORAGE
        # ====================================================

        self.future_signals: Dict[str, FutureSignal] = {}

        self.confirmed_signals: Dict[str, FutureSignal] = {}

        self.history: List[FutureSignal] = []

        # ====================================================
        # STATE
        # ====================================================

        self.running = False
        self.last_scan = 0
        self.scan_count = 0

        self._task = None

        # ====================================================
        # STATISTICS
        # ====================================================

        self.total_trades = 0
        self.wins = 0
        self.losses = 0

    # ========================================================
    # MARKET CONTROL
    # ========================================================

    def set_live_enabled(self, enabled: bool):
        self.live_enabled = bool(enabled)

    def set_otc_enabled(self, enabled: bool):
        self.otc_enabled = bool(enabled)

    # ========================================================
    # KEY
    # ========================================================

    @staticmethod
    def signal_key(pair: str, market: str) -> str:
        return f"{market}:{pair}"

    # ========================================================
    # PAIRS
    # ========================================================

    def get_pairs(self, market: str) -> List[str]:

        if not self.api_client:
            return []

        try:

            if hasattr(self.api_client, "get_pairs"):
                pairs = self.api_client.get_pairs(market)

                if asyncio.iscoroutine(pairs):
                    return []

                return list(pairs or [])

            if hasattr(self.api_client, "pairs"):
                pairs = self.api_client.pairs

                if isinstance(pairs, dict):
                    return list(
                        pairs.get(market, [])
                    )

                return list(pairs or [])

        except Exception:
            return []

        return []

    # ========================================================
    # CANDLE DATA
    # ========================================================

    async def get_candles(
        self,
        pair: str,
        market: str,
        timeframe: str,
        limit: int = 100,
    ) -> List[Candle]:

        if not self.api_client:
            return []

        try:

            method = None

            if hasattr(
                self.api_client,
                "get_candles"
            ):
                method = self.api_client.get_candles

            elif hasattr(
                self.api_client,
                "fetch_candles"
            ):
                method = self.api_client.fetch_candles

            if method is None:
                return []

            try:
                result = method(
                    pair=pair,
                    market=market,
                    timeframe=timeframe,
                    limit=limit,
                )

            except TypeError:

                result = method(
                    pair,
                    market,
                    timeframe,
                    limit,
                )

            if asyncio.iscoroutine(result):
                result = await result

            return self.normalize_candles(result)

        except Exception as error:

            print(
                f"Candle error "
                f"{market} {pair} {timeframe}: "
                f"{error}"
            )

            return []

    # ========================================================
    # NORMALIZE CANDLES
    # ========================================================

    @staticmethod
    def normalize_candles(
        data: Any
    ) -> List[Candle]:

        if not data:
            return []

        candles = []

        for item in data:

            try:

                if isinstance(item, Candle):

                    candles.append(item)
                    continue

                if isinstance(item, dict):

                    candles.append(
                        Candle(
                            open=float(
                                item["open"]
                            ),
                            high=float(
                                item["high"]
                            ),
                            low=float(
                                item["low"]
                            ),
                            close=float(
                                item["close"]
                            ),
                            timestamp=item.get(
                                "timestamp"
                            ),
                        )
                    )

                    continue

                if isinstance(item, (list, tuple)):

                    if len(item) >= 4:

                        timestamp = (
                            item[4]
                            if len(item) > 4
                            else None
                        )

                        candles.append(
                            Candle(
                                open=float(item[0]),
                                high=float(item[1]),
                                low=float(item[2]),
                                close=float(item[3]),
                                timestamp=timestamp,
                            )
                        )

            except (
                ValueError,
                TypeError,
                KeyError,
                IndexError,
            ):
                continue

        return candles

    # ========================================================
    # MULTI TIMEFRAME ANALYSIS
    # ========================================================

    async def analyze_pair(
        self,
        pair: str,
        market: str,
    ) -> Optional[FutureSignal]:

        candles_1m = await self.get_candles(
            pair,
            market,
            "1m",
            150,
        )

        if len(candles_1m) < 50:
            return None

        candles_5m = await self.get_candles(
            pair,
            market,
            "5m",
            100,
        )

        candles_15m = await self.get_candles(
            pair,
            market,
            "15m",
            100,
        )

        result = self.strategy.analyze(
            candles_1m,
            higher_timeframe_candles=(
                candles_5m
                if candles_5m
                else None
            ),
        )

        # ----------------------------------------------------
        # No useful direction
        # ----------------------------------------------------

        if not result.direction:
            return None

        now = int(time.time())

        levels = (
            self.strategy.support_resistance(
                candles_1m
            )
        )

        trend_1m = result.trend

        trend_5m = (
            self.strategy.trend(candles_5m)
            if candles_5m
            else "UNKNOWN"
        )

        trend_15m = (
            self.strategy.trend(candles_15m)
            if candles_15m
            else "UNKNOWN"
        )

        momentum = (
            self.strategy.momentum(
                candles_1m
            )
        )

        atr = (
            self.strategy.atr(
                candles_1m
            )
            or 0.0
        )

        key = self.signal_key(
            pair,
            market,
        )

        old_signal = (
            self.future_signals.get(key)
            or self.confirmed_signals.get(key)
        )

        confirmations = 1

        if old_signal:

            same_direction = (
                old_signal.direction
                == result.direction
            )

            if same_direction:
                confirmations = (
                    old_signal.confirmations + 1
                )

        # ----------------------------------------------------
        # Multi-timeframe confirmation
        # ----------------------------------------------------

        score = float(result.score)

        if (
            result.direction == "CALL"
            and trend_5m == "UP"
        ):
            score += 5

        elif (
            result.direction == "PUT"
            and trend_5m == "DOWN"
        ):
            score += 5

        if (
            result.direction == "CALL"
            and trend_15m == "UP"
        ):
            score += 5

        elif (
            result.direction == "PUT"
            and trend_15m == "DOWN"
        ):
            score += 5

        # Opposite higher timeframe = reduce confidence
        if (
            result.direction == "CALL"
            and trend_15m == "DOWN"
        ):
            score -= 5

        elif (
            result.direction == "PUT"
            and trend_15m == "UP"
        ):
            score -= 5

        score = max(
            0.0,
            min(score, 100.0)
        )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        if score >= 80:

            status = "CONFIRMED"
            confidence = "HIGH"

        elif score >= 65:

            status = "MONITOR"
            confidence = "MEDIUM"

        elif score >= 55:

            status = "FUTURE"
            confidence = "LOW"

        else:

            return None

        # ----------------------------------------------------
        # Expiry
        # ----------------------------------------------------

        expires_at = (
            now +
            self.signal_ttl_seconds
        )

        signal = FutureSignal(

            pair=pair,
            market=market,

            direction=result.direction,

            score=round(score, 2),

            confidence=confidence,
            status=status,

            signal_time=now,

            expiry_minutes=1,

            support=levels["support"],
            resistance=levels["resistance"],

            reasons=list(
                result.reasons
            ),

            trend_1m=trend_1m,
            trend_5m=trend_5m,
            trend_15m=trend_15m,

            momentum=momentum,

            volatility=float(atr),

            last_update=now,
            expires_at=expires_at,

            result="PENDING",

            confirmations=confirmations,
        )

        return signal

    # ========================================================
    # SAVE SIGNAL
    # ========================================================

    def save_signal(
        self,
        signal: FutureSignal,
    ):

        key = self.signal_key(
            signal.pair,
            signal.market,
        )

        # Confirmed signals
        if signal.status == "CONFIRMED":

            self.confirmed_signals[key] = signal

            self.future_signals.pop(
                key,
                None,
            )

        else:

            self.future_signals[key] = signal

            self.confirmed_signals.pop(
                key,
                None,
            )

        # Limit future signals
        if (
            len(self.future_signals)
            > self.max_future_signals
        ):

            oldest_key = min(
                self.future_signals,
                key=lambda k:
                    self.future_signals[k].signal_time,
            )

            self.future_signals.pop(
                oldest_key,
                None,
            )

    # ========================================================
    # SCAN ONE MARKET
    # ========================================================

    async def scan_market(
        self,
        market: str,
    ):

        if market == "LIVE":
            if not self.live_enabled:
                return

        if market == "OTC":
            if not self.otc_enabled:
                return

        pairs = self.get_pairs(
            market
        )

        if not pairs:
            return

        # Don't hammer the API
        semaphore = asyncio.Semaphore(5)

        async def scan_pair(pair):

            async with semaphore:

                try:

                    signal = await self.analyze_pair(
                        pair,
                        market,
                    )

                    if signal:
                        self.save_signal(
                            signal
                        )

                except Exception as error:

                    print(
                        f"Scan error "
                        f"{market} {pair}: "
                        f"{error}"
                    )

        await asyncio.gather(
            *[
                scan_pair(pair)
                for pair in pairs
            ],
            return_exceptions=True,
        )

    # ========================================================
    # EXPIRE SIGNALS
    # ========================================================

    def cleanup_expired(self):

        now = int(time.time())

        expired = []

        for key, signal in list(
            self.future_signals.items()
        ):

            if (
                signal.expires_at > 0
                and now >= signal.expires_at
            ):

                expired.append(
                    (
                        key,
                        signal,
                    )
                )

        for key, signal in expired:

            self.history.append(
                signal
            )

            self.future_signals.pop(
                key,
                None,
            )

        # Keep history under control
        if len(self.history) > 500:

            self.history = (
                self.history[-500:]
            )

    # ========================================================
    # FULL SCAN
    # ========================================================

    async def scan_once(self):

        self.scan_count += 1
        self.last_scan = int(
            time.time()
        )

        await asyncio.gather(

            self.scan_market("LIVE"),

            self.scan_market("OTC"),

            return_exceptions=True,
        )

        self.cleanup_expired()

    # ========================================================
    # START
    # ========================================================

    async def start(self):

        if self.running:
            return

        self.running = True

        print(
            "Market scanner started."
        )

        while self.running:

            try:

                await self.scan_once()

            except Exception as error:

                print(
                    f"Scanner error: {error}"
                )

            await asyncio.sleep(
                self.rescan_interval
            )

    # ========================================================
    # STOP
    # ========================================================

    async def stop(self):

        self.running = False

        print(
            "Market scanner stopped."
        )

    # ========================================================
    # BACKGROUND START
    # ========================================================

    def start_background(self):

        if self.running:
            return

        try:

            loop = asyncio.get_running_loop()

            self._task = loop.create_task(
                self.start()
            )

        except RuntimeError:

            self._task = None

    # ========================================================
    # BACKGROUND STOP
    # ========================================================

    async def stop_background(self):

        self.running = False

        if self._task:

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

    # ========================================================
    # FUTURE SIGNAL LIST
    # ========================================================

    def get_future_signals(
        self,
        market: Optional[str] = None,
    ) -> List[Dict]:

        signals = list(
            self.future_signals.values()
        )

        if market:

            signals = [
                signal
                for signal in signals
                if signal.market == market
            ]

        signals.sort(
            key=lambda signal:
                signal.score,
            reverse=True,
        )

        return [
            signal.to_dict()
            for signal in signals
        ]

    # ========================================================
    # CONFIRMED SIGNAL LIST
    # ========================================================

    def get_confirmed_signals(
        self,
        market: Optional[str] = None,
    ) -> List[Dict]:

        signals = list(
            self.confirmed_signals.values()
        )

        if market:

            signals = [
                signal
                for signal in signals
                if signal.market == market
            ]

        signals.sort(
            key=lambda signal:
                signal.score,
            reverse=True,
        )

        return [
            signal.to_dict()
            for signal in signals
        ]

    # ========================================================
    # STATISTICS
    # ========================================================

    def get_statistics(self) -> Dict:

        total = self.total_trades
        wins = self.wins
        losses = self.losses

        if total > 0:

            accuracy = (
                wins / total
            ) * 100

        else:

            accuracy = 0.0

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "accuracy": round(
                accuracy,
                2,
            ),
            "scan_count": self.scan_count,
            "last_scan": self.last_scan,
        }

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self) -> Dict:

        return {
            "running": self.running,

            "live_enabled":
                self.live_enabled,

            "otc_enabled":
                self.otc_enabled,

            "future_signals":
                len(self.future_signals),

            "confirmed_signals":
                len(self.confirmed_signals),

            "scan_count":
                self.scan_count,

            "last_scan":
                self.last_scan,
        }

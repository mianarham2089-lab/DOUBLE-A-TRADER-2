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

        self.api_client = api_client

        self.strategy = StrategyEngine(
            future_score=future_score,
            monitor_score=monitor_score,
            confirmed_score=confirmed_score,
        )

        self.future_score = future_score
        self.monitor_score = monitor_score
        self.confirmed_score = confirmed_score

        self.live_enabled = True
        self.otc_enabled = True

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
            str,
            FutureSignal
        ] = {}

        self.history: List[
            FutureSignal
        ] = []

        self.running = False

        self.last_scan = 0
        self.scan_count = 0

        self._task = None

    # ========================================================
    # MARKET CONTROL
    # ========================================================

    def set_live_enabled(
        self,
        enabled: bool
    ):

        self.live_enabled = bool(
            enabled
        )

    def set_otc_enabled(
        self,
        enabled: bool
    ):

        self.otc_enabled = bool(
            enabled
        )

    # ========================================================
    # START / STOP
    # ========================================================

    async def run(self):

        if self.running:
            return

        self.running = True

        try:

            while self.running:

                await self.scan_once()

                await asyncio.sleep(
                    self.rescan_interval
                )

        except asyncio.CancelledError:

            pass

        finally:

            self.running = False

    def stop(self):

        self.running = False

        if self._task:

            try:
                self._task.cancel()
            except Exception:
                pass

            self._task = None

    # ========================================================
    # SCAN
    # ========================================================

    async def scan_once(self):

        self.last_scan = int(
            time.time()
        )

        self.scan_count += 1

        if not self.api_client:
            return

        try:

            markets = (
                await self.api_client
                .get_available_assets()
            )

        except Exception:

            return

        if not isinstance(
            markets,
            dict
        ):
            return

        market_groups = []

        if self.live_enabled:

            market_groups.append(
                (
                    "LIVE",
                    markets.get(
                        "LIVE",
                        []
                    )
                )
            )

        if self.otc_enabled:

            market_groups.append(
                (
                    "OTC",
                    markets.get(
                        "OTC",
                        []
                    )
                )
            )

        for market, pairs in market_groups:

            if not pairs:
                continue

            for pair in pairs:

                try:

                    await self.analyze_pair(
                        pair,
                        market
                    )

                except Exception:

                    continue

        self.cleanup_expired()

    # ========================================================
    # PAIR ANALYSIS
    # ========================================================

    async def analyze_pair(
        self,
        pair: str,
        market: str
    ):

        if not self.api_client:
            return

        candles_1m = await self._get_candles(
            pair,
            market,
            60
        )

        candles_5m = await self._get_candles(
            pair,
            market,
            300
        )

        candles_15m = await self._get_candles(
            pair,
            market,
            900
        )

        if len(candles_1m) < 20:
            return

        signal = self.strategy.analyze(
            candles_1m,
            candles_5m,
            candles_15m
        )

        if not signal:
            return

        if signal.direction == "WAIT":
            return

        score = float(
            getattr(
                signal,
                "score",
                0
            )
        )

        if score < self.future_score:
            return

        levels = (
            self.strategy.support_resistance(
                candles_1m
            )
        )

        trend_1m = self._trend(
            candles_1m
        )

        trend_5m = self._trend(
            candles_5m
        )

        trend_15m = self._trend(
            candles_15m
        )

        momentum = self._momentum(
            candles_1m
        )

        volatility = self._volatility(
            candles_1m
        )

        now = int(
            time.time()
        )

        key = (
            f"{market}:{pair}"
        )

        old = self.future_signals.get(
            key
        )

        confirmations = 1

        if old:

            confirmations = (
                old.confirmations + 1
            )

        if score >= self.confirmed_score:

            status = "CONFIRMED"

        elif score >= self.monitor_score:

            status = "MONITOR"

        else:

            status = "FUTURE"

        future = FutureSignal(

            pair=pair,
            market=market,

            direction=(
                "CALL"
                if signal.direction == "UP"
                else "PUT"
            ),

            score=score,

            confidence=self._confidence(
                score
            ),

            status=status,

            signal_time=now,

            support=levels.get(
                "support",
                0.0
            ),

            resistance=levels.get(
                "resistance",
                0.0
            ),

            reasons=list(
                getattr(
                    signal,
                    "reasons",
                    []
                )
            ),

            trend_1m=trend_1m,
            trend_5m=trend_5m,
            trend_15m=trend_15m,

            momentum=momentum,
            volatility=volatility,

            last_update=now,

            expires_at=(
                now +
                self.signal_ttl_seconds
            ),

            result="PENDING",

            confirmations=confirmations,
        )

        self.future_signals[key] = future

        self._limit_future_signals()

    # ========================================================
    # CANDLE DATA
    # ========================================================

    async def _get_candles(
        self,
        pair: str,
        market: str,
        timeframe: int
    ) -> List[Candle]:

        try:

            raw = await self.api_client.get_candles(
                pair=pair,
                market=market,
                timeframe=timeframe,
                count=100,
            )

        except Exception:

            return []

        candles = []

        for item in raw or []:

            try:

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
                    )
                )

            except Exception:

                continue

        return candles

    # ========================================================
    # TREND
    # ========================================================

    @staticmethod
    def _trend(
        candles: List[Candle]
    ) -> str:

        if len(candles) < 5:
            return "UNKNOWN"

        closes = [
            c.close
            for c in candles[-5:]
        ]

        if (
            closes[-1] > closes[0]
            and closes[-1] > closes[-2]
        ):

            return "UP"

        if (
            closes[-1] < closes[0]
            and closes[-1] < closes[-2]
        ):

            return "DOWN"

        return "SIDEWAYS"

    # ========================================================
    # MOMENTUM
    # ========================================================

    @staticmethod
    def _momentum(
        candles: List[Candle]
    ) -> str:

        if len(candles) < 5:
            return "UNKNOWN"

        recent = candles[-5:]

        bullish = sum(
            1
            for c in recent
            if c.close > c.open
        )

        bearish = sum(
            1
            for c in recent
            if c.close < c.open
        )

        if bullish >= 4:
            return "STRONG_UP"

        if bearish >= 4:
            return "STRONG_DOWN"

        if bullish > bearish:
            return "UP"

        if bearish > bullish:
            return "DOWN"

        return "NEUTRAL"

    # ========================================================
    # VOLATILITY
    # ========================================================

    @staticmethod
    def _volatility(
        candles: List[Candle]
    ) -> float:

        if not candles:
            return 0.0

        recent = candles[-20:]

        ranges = [
            abs(
                c.high - c.low
            )
            for c in recent
        ]

        if not ranges:
            return 0.0

        return sum(ranges) / len(
            ranges
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    @staticmethod
    def _confidence(
        score: float
    ) -> str:

        if score >= 90:
            return "VERY HIGH"

        if score >= 80:
            return "HIGH"

        if score >= 70:
            return "MEDIUM-HIGH"

        if score >= 60:
            return "MEDIUM"

        return "LOW"

    # ========================================================
    # LIMIT SIGNALS
    # ========================================================

    def _limit_future_signals(self):

        if len(
            self.future_signals
        ) <= self.max_future_signals:

            return

        ordered = sorted(
            self.future_signals.items(),
            key=lambda x: x[1].score,
            reverse=True
        )

        keep = dict(
            ordered[
                :self.max_future_signals
            ]
        )

        self.future_signals = keep

    # ========================================================
    # EXPIRY
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
                and now >
                signal.expires_at
            ):

                signal.status = "EXPIRED"

                self.history.append(
                    signal
                )

                expired.append(
                    key
                )

        for key in expired:

            self.future_signals.pop(
                key,
                None
            )

    # ========================================================
    # RESULT UPDATE
    # ========================================================

    def update_result(
        self,
        pair: str,
        market: str,
        result: str
    ) -> bool:

        key = (
            f"{market}:{pair}"
        )

        signal = (
            self.future_signals.get(
                key
            )
        )

        if not signal:
            return False

        result = result.upper()

        if result not in {
            "WIN",
            "LOSS",
            "DRAW"
        }:

            return False

        signal.result = result

        signal.status = result

        signal.last_update = int(
            time.time()
        )

        self.history.append(
            signal
        )

        return True

    # ========================================================
    # GETTERS
    # ========================================================

    def get_future_list(
        self
    ) -> List[FutureSignal]:

        return sorted(
            self.future_signals.values(),
            key=lambda x: x.score,
            reverse=True
        )

    def get_confirmed(
        self
    ) -> List[FutureSignal]:

        return [
            signal
            for signal
            in self.future_signals.values()
            if signal.status
            == "CONFIRMED"
        ]

    def get_market_list(
        self,
        market: str
    ) -> List[FutureSignal]:

        return [
            signal
            for signal
            in self.future_signals.values()
            if signal.market
            == market
        ]

    # ========================================================
    # STATISTICS
    # ========================================================

    def statistics(self):

        completed = [
            signal
            for signal in self.history
            if signal.result
            in {
                "WIN",
                "LOSS"
            }
        ]

        wins = sum(
            1
            for signal in completed
            if signal.result
            == "WIN"
        )

        losses = sum(
            1
            for signal in completed
            if signal.result
            == "LOSS"
        )

        total = wins + losses

        accuracy = (
            (wins / total) * 100
            if total
            else 0.0
        )

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "accuracy": round(
                accuracy,
                2
            ),
            "scan_count":
                self.scan_count,
            "last_scan":
                self.last_scan,
        }

    # ========================================================
    # DASHBOARD
    # ========================================================

    def dashboard_data(self):

        return {

            "scanner": {
                "running":
                    self.running,

                "live_enabled":
                    self.live_enabled,

                "otc_enabled":
                    self.otc_enabled,

                "last_scan":
                    self.last_scan,

                "scan_count":
                    self.scan_count,
            },

            "future_signals": [
                signal.to_dict()
                for signal
                in self.get_future_list()
            ],

            "confirmed": [
                signal.to_dict()
                for signal
                in self.get_confirmed()
            ],

            "statistics":
                self.statistics(),
        }

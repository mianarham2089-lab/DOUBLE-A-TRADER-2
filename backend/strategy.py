from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: Optional[int] = None


@dataclass
class Signal:
    direction: str
    score: float
    confidence: str
    status: str

    reasons: List[str] = field(default_factory=list)

    trend: str = "UNKNOWN"
    support: float = 0.0
    resistance: float = 0.0

    indicators: Dict[str, float] = field(
        default_factory=dict
    )


# ============================================================
# STRATEGY ENGINE
# ============================================================

class StrategyEngine:

    def __init__(
        self,
        future_score: float = 55.0,
        monitor_score: float = 65.0,
        confirmed_score: float = 75.0,
    ):

        self.future_score = future_score
        self.monitor_score = monitor_score
        self.confirmed_score = confirmed_score

    # ========================================================
    # BASIC HELPERS
    # ========================================================

    @staticmethod
    def closes(
        candles: List[Candle]
    ) -> List[float]:

        return [
            float(c.close)
            for c in candles
        ]

    @staticmethod
    def ema(
        values: List[float],
        period: int
    ) -> Optional[float]:

        if len(values) < period:
            return None

        multiplier = 2 / (period + 1)

        value = sum(
            values[:period]
        ) / period

        for price in values[period:]:

            value += (
                price - value
            ) * multiplier

        return value

    # ========================================================
    # RSI
    # ========================================================

    @staticmethod
    def rsi(
        values: List[float],
        period: int = 14
    ) -> Optional[float]:

        if len(values) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(
            1,
            len(values)
        ):

            change = (
                values[i]
                - values[i - 1]
            )

            gains.append(
                max(change, 0)
            )

            losses.append(
                max(-change, 0)
            )

        avg_gain = (
            sum(gains[:period])
            / period
        )

        avg_loss = (
            sum(losses[:period])
            / period
        )

        for i in range(
            period,
            len(gains)
        ):

            avg_gain = (
                (
                    avg_gain
                    * (period - 1)
                )
                + gains[i]
            ) / period

            avg_loss = (
                (
                    avg_loss
                    * (period - 1)
                )
                + losses[i]
            ) / period

        if avg_loss == 0:
            return 100.0

        rs = (
            avg_gain
            / avg_loss
        )

        return 100 - (
            100 / (1 + rs)
        )

    # ========================================================
    # MACD
    # ========================================================

    @classmethod
    def macd(
        cls,
        values: List[float]
    ) -> Tuple[
        Optional[float],
        Optional[float],
        Optional[float]
    ]:

        if len(values) < 35:

            return (
                None,
                None,
                None
            )

        macd_values = []

        for i in range(
            26,
            len(values) + 1
        ):

            section = values[:i]

            ema12 = cls.ema(
                section,
                12
            )

            ema26 = cls.ema(
                section,
                26
            )

            if (
                ema12 is not None
                and ema26 is not None
            ):

                macd_values.append(
                    ema12 - ema26
                )

        if not macd_values:

            return (
                None,
                None,
                None
            )

        macd_line = (
            macd_values[-1]
        )

        signal_line = cls.ema(
            macd_values,
            9
        )

        if signal_line is None:

            signal_line = (
                sum(macd_values)
                / len(macd_values)
            )

        histogram = (
            macd_line
            - signal_line
        )

        return (
            macd_line,
            signal_line,
            histogram
        )

    # ========================================================
    # ATR
    # ========================================================

    @staticmethod
    def atr(
        candles: List[Candle],
        period: int = 14
    ) -> Optional[float]:

        if len(candles) < period + 1:
            return None

        ranges = []

        for i in range(
            1,
            len(candles)
        ):

            current = candles[i]
            previous = candles[i - 1]

            true_range = max(
                current.high
                - current.low,

                abs(
                    current.high
                    - previous.close
                ),

                abs(
                    current.low
                    - previous.close
                )
            )

            ranges.append(
                true_range
            )

        if len(ranges) < period:
            return None

        return (
            sum(ranges[-period:])
            / period
        )

    # ========================================================
    # TREND
    # ========================================================

    @classmethod
    def trend(
        cls,
        candles: List[Candle]
    ) -> str:

        if len(candles) < 20:
            return "UNKNOWN"

        values = cls.closes(
            candles
        )

        ema9 = cls.ema(
            values,
            9
        )

        ema20 = cls.ema(
            values,
            20
        )

        if (
            ema9 is None
            or ema20 is None
        ):

            return "UNKNOWN"

        recent = values[-5:]

        rising = (
            recent[-1]
            > recent[0]
        )

        falling = (
            recent[-1]
            < recent[0]
        )

        if (
            ema9 > ema20
            and rising
        ):

            return "UP"

        if (
            ema9 < ema20
            and falling
        ):

            return "DOWN"

        return "SIDEWAYS"

    # ========================================================
    # SUPPORT / RESISTANCE
    # ========================================================

    @staticmethod
    def support_resistance(
        candles: List[Candle],
        lookback: int = 30
    ) -> Dict[str, float]:

        if not candles:

            return {
                "support": 0.0,
                "resistance": 0.0
            }

        recent = candles[
            -lookback:
        ]

        return {
            "support": min(
                c.low
                for c in recent
            ),

            "resistance": max(
                c.high
                for c in recent
            )
        }

    # ========================================================
    # PRICE ACTION
    # ========================================================

    @staticmethod
    def candle_signal(
        candles: List[Candle]
    ) -> Tuple[
        Optional[str],
        List[str]
    ]:

        if len(candles) < 3:

            return (
                None,
                []
            )

        current = candles[-1]
        previous = candles[-2]

        candle_range = (
            current.high
            - current.low
        )

        if candle_range <= 0:

            return (
                None,
                []
            )

        body = abs(
            current.close
            - current.open
        )

        upper_wick = (
            current.high
            - max(
                current.open,
                current.close
            )
        )

        lower_wick = (
            min(
                current.open,
                current.close
            )
            - current.low
        )

        body_ratio = (
            body / candle_range
        )

        reasons = []

        # Strong bullish candle
        if (
            current.close
            > current.open
            and body_ratio >= 0.55
            and current.close
            > previous.close
        ):

            reasons.append(
                "Strong bullish candle"
            )

            return (
                "UP",
                reasons
            )

        # Strong bearish candle
        if (
            current.close
            < current.open
            and body_ratio >= 0.55
            and current.close
            < previous.close
        ):

            reasons.append(
                "Strong bearish candle"
            )

            return (
                "DOWN",
                reasons
            )

        # Bullish rejection
        if (
            lower_wick
            > body * 1.5
            and lower_wick
            > upper_wick
        ):

            reasons.append(
                "Bullish rejection"
            )

            return (
                "UP",
                reasons
            )

        # Bearish rejection
        if (
            upper_wick
            > body * 1.5
            and upper_wick
            > lower_wick
        ):

            reasons.append(
                "Bearish rejection"
            )

            return (
                "DOWN",
                reasons
            )

        return (
            None,
            reasons
        )

    # ========================================================
    # MOMENTUM
    # ========================================================

    @staticmethod
    def momentum(
        candles: List[Candle],
        lookback: int = 5
    ) -> str:

        if len(candles) < (
            lookback + 1
        ):

            return "UNKNOWN"

        old_price = candles[
            -lookback - 1
        ].close

        current_price = candles[
            -1
        ].close

        if current_price > old_price:
            return "UP"

        if current_price < old_price:
            return "DOWN"

        return "FLAT"

    # ========================================================
    # BREAKOUT
    # ========================================================

    @staticmethod
    def breakout_signal(
        candles: List[Candle],
        levels: Dict[str, float]
    ) -> Optional[str]:

        if len(candles) < 3:
            return None

        current = candles[-1]
        previous = candles[-2]

        support = levels[
            "support"
        ]

        resistance = levels[
            "resistance"
        ]

        if (
            previous.close
            <= resistance
            and current.close
            > resistance
        ):

            return "UP"

        if (
            previous.close
            >= support
            and current.close
            < support
        ):

            return "DOWN"

        return None

    # ========================================================
    # MULTI TIMEFRAME
    # ========================================================

    @classmethod
    def timeframe_alignment(
        cls,
        candles_1m: List[Candle],
        candles_5m: List[Candle],
        candles_15m: List[Candle]
    ) -> Tuple[
        str,
        float,
        List[str]
    ]:

        trend_1m = cls.trend(
            candles_1m
        )

        trend_5m = cls.trend(
            candles_5m
        )

        trend_15m = cls.trend(
            candles_15m
        )

        bonus = 0.0
        reasons = []

        trends = [
            trend_1m,
            trend_5m,
            trend_15m
        ]

        up_count = trends.count(
            "UP"
        )

        down_count = trends.count(
            "DOWN"
        )

        if up_count == 3:

            bonus += 20
            reasons.append(
                "1M/5M/15M all UP"
            )

            return (
                "UP",
                bonus,
                reasons
            )

        if down_count == 3:

            bonus += 20
            reasons.append(
                "1M/5M/15M all DOWN"
            )

            return (
                "DOWN",
                bonus,
                reasons
            )

        if up_count >= 2:

            bonus += 10
            reasons.append(
                "Multi-timeframe bullish"
            )

            return (
                "UP",
                bonus,
                reasons
            )

        if down_count >= 2:

            bonus += 10
            reasons.append(
                "Multi-timeframe bearish"
            )

            return (
                "DOWN",
                bonus,
                reasons
            )

        return (
            "MIXED",
            0.0,
            [
                "Timeframes are mixed"
            ]
        )

    # ========================================================
    # ANALYSIS
    # ========================================================

    def analyze(
        self,
        candles_1m: List[Candle],
        candles_5m: Optional[
            List[Candle]
        ] = None,
        candles_15m: Optional[
            List[Candle]
        ] = None
    ) -> Signal:

        if len(candles_1m) < 20:

            return Signal(
                direction="WAIT",
                score=0.0,
                confidence="LOW",
                status="NO_DATA",
                reasons=[
                    "Not enough 1M candle data"
                ]
            )

        if candles_5m is None:
            candles_5m = []

        if candles_15m is None:
            candles_15m = []

        values = self.closes(
            candles_1m
        )

        up = 0.0
        down = 0.0

        up_reasons = []
        down_reasons = []

        # ----------------------------------------------------
        # TREND
        # ----------------------------------------------------

        trend_1m = self.trend(
            candles_1m
        )

        if trend_1m == "UP":

            up += 15

            up_reasons.append(
                "1M uptrend"
            )

        elif trend_1m == "DOWN":

            down += 15

            down_reasons.append(
                "1M downtrend"
            )

        # ----------------------------------------------------
        # EMA
        # ----------------------------------------------------

        ema9 = self.ema(
            values,
            9
        )

        ema20 = self.ema(
            values,
            20
        )

        ema50 = self.ema(
            values,
            50
        )

        if (
            ema9 is not None
            and ema20 is not None
            and ema50 is not None
        ):

            if (
                ema9
                > ema20
                > ema50
            ):

                up += 15

                up_reasons.append(
                    "EMA 9/20/50 bullish alignment"
                )

            elif (
                ema9
                < ema20
                < ema50
            ):

                down += 15

                down_reasons.append(
                    "EMA 9/20/50 bearish alignment"
                )

        # ----------------------------------------------------
        # RSI
        # ----------------------------------------------------

        rsi_value = self.rsi(
            values
        )

        if rsi_value is not None:

            if (
                50
                <= rsi_value
                <= 68
            ):

                up += 8

                up_reasons.append(
                    f"RSI bullish ({rsi_value:.1f})"
                )

            elif (
                32
                <= rsi_value
                < 50
            ):

                down += 8

                down_reasons.append(
                    f"RSI bearish ({rsi_value:.1f})"
                )

        # ----------------------------------------------------
        # MACD
        # ----------------------------------------------------

        (
            macd_line,
            macd_signal,
            histogram
        ) = self.macd(values)

        if (
            macd_line is not None
            and macd_signal is not None
            and histogram is not None
        ):

            if (
                macd_line
                > macd_signal
                and histogram > 0
            ):

                up += 8

                up_reasons.append(
                    "MACD bullish"
                )

            elif (
                macd_line
                < macd_signal
                and histogram < 0
            ):

                down += 8

                down_reasons.append(
                    "MACD bearish"
                )

        # ----------------------------------------------------
        # SUPPORT / RESISTANCE
        # ----------------------------------------------------

        levels = (
            self.support_resistance(
                candles_1m
            )
        )

        support = levels[
            "support"
        ]

        resistance = levels[
            "resistance"
        ]

        price = candles_1m[
            -1
        ].close

        price_range = (
            resistance
            - support
        )

        if price_range > 0:

            position = (
                (price - support)
                / price_range
            )

            if position <= 0.25:

                up += 10

                up_reasons.append(
                    "Price near support"
                )

            elif position >= 0.75:

                down += 10

                down_reasons.append(
                    "Price near resistance"
                )

        # ----------------------------------------------------
        # PRICE ACTION
        # ----------------------------------------------------

        (
            candle_direction,
            candle_reasons
        ) = self.candle_signal(
            candles_1m
        )

        if candle_direction == "UP":

            up += 10

            up_reasons.extend(
                candle_reasons
            )

        elif candle_direction == "DOWN":

            down += 10

            down_reasons.extend(
                candle_reasons
            )

        # ----------------------------------------------------
        # MOMENTUM
        # ----------------------------------------------------

        momentum = self.momentum(
            candles_1m
        )

        if momentum == "UP":

            up += 5

            up_reasons.append(
                "Short-term momentum UP"
            )

        elif momentum == "DOWN":

            down += 5

            down_reasons.append(
                "Short-term momentum DOWN"
            )

        # ----------------------------------------------------
        # BREAKOUT
        # ----------------------------------------------------

        breakout = (
            self.breakout_signal(
                candles_1m,
                levels
            )
        )

        if breakout == "UP":

            up += 10

            up_reasons.append(
                "Resistance breakout"
            )

        elif breakout == "DOWN":

            down += 10

            down_reasons.append(
                "Support breakdown"
            )

        # ----------------------------------------------------
        # MULTI-TIMEFRAME CONFIRMATION
        # ----------------------------------------------------

        if (
            candles_5m
            and candles_15m
        ):

            (
                mtf_direction,
                mtf_bonus,
                mtf_reasons
            ) = self.timeframe_alignment(
                candles_1m,
                candles_5m,
                candles_15m
            )

            if mtf_direction == "UP":

                up += mtf_bonus
                up_reasons.extend(
                    mtf_reasons
                )

            elif mtf_direction == "DOWN":

                down += mtf_bonus
                down_reasons.extend(
                    mtf_reasons
                )

        # ----------------------------------------------------
        # FINAL DIRECTION
        # ----------------------------------------------------

        if up > down:

            direction = "UP"
            score = up
            reasons = up_reasons

        elif down > up:

            direction = "DOWN"
            score = down
            reasons = down_reasons

        else:

            return Signal(
                direction="WAIT",
                score=0.0,
                confidence="LOW",
                status="WAIT",
                reasons=[
                    "No directional advantage"
                ],
                trend=trend_1m,
                support=support,
                resistance=resistance
            )

        # ----------------------------------------------------
        # CONFLICT FILTER
        # ----------------------------------------------------

        difference = abs(
            up - down
        )

        if difference < 8:

            return Signal(
                direction="WAIT",
                score=round(
                    score,
                    2
                ),
                confidence="LOW",
                status="WAIT",
                reasons=[
                    "Directional conflict"
                ],
                trend=trend_1m,
                support=support,
                resistance=resistance
            )

        # ----------------------------------------------------
        # SCORE CAP
        # ----------------------------------------------------

        score = min(
            score,
            100.0
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if score >= self.confirmed_score:

            status = "CONFIRMED"
            confidence = "HIGH"

        elif score >= self.monitor_score:

            status = "MONITOR"
            confidence = "MEDIUM"

        elif score >= self.future_score:

            status = "FUTURE"
            confidence = "LOW"

        else:

            status = "WAIT"
            confidence = "LOW"

        # ----------------------------------------------------
        # INDICATORS
        # ----------------------------------------------------

        atr_value = self.atr(
            candles_1m
        )

        indicators = {

            "ema9":
                round(
                    ema9 or 0.0,
                    8
                ),

            "ema20":
                round(
                    ema20 or 0.0,
                    8
                ),

            "ema50":
                round(
                    ema50 or 0.0,
                    8
                ),

            "rsi":
                round(
                    rsi_value or 0.0,
                    2
                ),

            "macd":
                round(
                    macd_line or 0.0,
                    8
                ),

            "macd_signal":
                round(
                    macd_signal or 0.0,
                    8
                ),

            "macd_histogram":
                round(
                    histogram or 0.0,
                    8
                ),

            "atr":
                round(
                    atr_value or 0.0,
                    8
                )
        }

        # ----------------------------------------------------
        # RETURN
        # ----------------------------------------------------

        return Signal(

            direction=direction,

            score=round(
                score,
                2
            ),

            confidence=confidence,

            status=status,

            reasons=reasons,

            trend=trend_1m,

            support=support,

            resistance=resistance,

            indicators=indicators
        )

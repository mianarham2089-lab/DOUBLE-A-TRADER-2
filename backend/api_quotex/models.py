from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    timestamp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "timestamp": self.timestamp,
        }


@dataclass
class Asset:
    symbol: str
    name: str = ""
    market: str = "LIVE"
    payout: float = 0.0
    is_open: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "payout": self.payout,
            "is_open": self.is_open,
        }

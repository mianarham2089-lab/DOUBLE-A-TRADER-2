from typing import Any, Dict, List, Optional


def normalize_market(symbol: str) -> str:
    """
    Detect whether an asset is LIVE or OTC.
    """
    if symbol.lower().endswith("_otc"):
        return "OTC"

    return "LIVE"


def normalize_symbol(symbol: str) -> str:
    """
    Keep the original Quotex symbol.
    """
    return str(symbol).strip()


def is_otc(symbol: str) -> bool:
    return normalize_market(symbol) == "OTC"


def is_live(symbol: str) -> bool:
    return normalize_market(symbol) == "LIVE"


def candle_from_dict(data: Dict[str, Any]):
    """
    Convert common candle dictionary formats
    into our Candle model.
    """
    from .models import Candle

    return Candle(
        open=float(data.get("open", data.get("o", 0))),
        high=float(data.get("high", data.get("h", 0))),
        low=float(data.get("low", data.get("l", 0))),
        close=float(data.get("close", data.get("c", 0))),
        timestamp=data.get(
            "timestamp",
            data.get("time", data.get("at"))
        ),
    )


def normalize_candles(
    candles: Optional[List[Dict[str, Any]]],
):
    """
    Convert a list of raw candle dictionaries
    into Candle objects.
    """
    if not candles:
        return []

    result = []

    for candle in candles:
        try:
            result.append(
                candle_from_dict(candle)
            )
        except (TypeError, ValueError):
            continue

    return result

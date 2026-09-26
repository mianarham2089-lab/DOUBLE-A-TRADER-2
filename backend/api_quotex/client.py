import os
from typing import Any, Dict, List, Optional

from .config import QuotexConfig
from .exceptions import (
    QuotexAuthenticationError,
    QuotexConnectionError,
    QuotexDataError,
)
from .models import Asset, Candle
from .utils import normalize_market, normalize_symbol


class QuotexClient:
    """
    Central Quotex API/client interface.

    This class does not generate fake candles or signals.
    A real Quotex-compatible transport/client must be supplied
    through the transport object.
    """

    def __init__(
        self,
        config: Optional[QuotexConfig] = None,
        transport: Any = None,
    ):
        self.config = config or QuotexConfig.from_environment()
        self.transport = transport

        self.connected = False
        self.authenticated = False

    async def connect(self) -> bool:
        if self.transport is None:
            raise QuotexConnectionError(
                "No Quotex transport/client has been configured."
            )

        try:
            result = self.transport.connect()

            if hasattr(result, "__await__"):
                result = await result

            self.connected = bool(result)

            if not self.connected:
                raise QuotexConnectionError(
                    "Quotex connection failed."
                )

            self.authenticated = True
            return True

        except QuotexConnectionError:
            raise

        except Exception as exc:
            self.connected = False
            self.authenticated = False

            raise QuotexConnectionError(
                str(exc)
            ) from exc

    async def disconnect(self):
        if self.transport is None:
            self.connected = False
            self.authenticated = False
            return

        try:
            result = self.transport.disconnect()

            if hasattr(result, "__await__"):
                await result

        finally:
            self.connected = False
            self.authenticated = False

    def _require_connection(self):
        if not self.connected or not self.authenticated:
            raise QuotexAuthenticationError(
                "Quotex client is not connected/authenticated."
            )

    async def get_assets(self) -> List[Asset]:
        self._require_connection()

        if not hasattr(self.transport, "get_assets"):
            raise QuotexDataError(
                "Transport does not provide get_assets()."
            )

        result = self.transport.get_assets()

        if hasattr(result, "__await__"):
            result = await result

        assets = []

        for item in result or []:
            if isinstance(item, Asset):
                assets.append(item)
                continue

            if not isinstance(item, dict):
                continue

            symbol = normalize_symbol(
                item.get("symbol", "")
            )

            if not symbol:
                continue

            assets.append(
                Asset(
                    symbol=symbol,
                    name=str(
                        item.get("name", "")
                    ),
                    market=normalize_market(
                        symbol
                    ),
                    payout=float(
                        item.get("payout", 0) or 0
                    ),
                    is_open=bool(
                        item.get("is_open", True)
                    ),
                )
            )

        return assets

    async def get_candles(
        self,
        symbol: str,
        timeframe: int = 60,
        count: int = 100,
    ) -> List[Candle]:

        self._require_connection()

        if not hasattr(
            self.transport,
            "get_candles",
        ):
            raise QuotexDataError(
                "Transport does not provide get_candles()."
            )

        result = self.transport.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
        )

        if hasattr(result, "__await__"):
            result = await result

        if not isinstance(result, list):
            raise QuotexDataError(
                "Invalid candle response."
            )

        candles = []

        for item in result:

            if isinstance(item, Candle):
                candles.append(item)
                continue

            if not isinstance(item, dict):
                continue

            try:
                candles.append(
                    Candle(
                        open=float(
                            item.get(
                                "open",
                                item.get("o", 0)
                            )
                        ),
                        high=float(
                            item.get(
                                "high",
                                item.get("h", 0)
                            )
                        ),
                        low=float(
                            item.get(
                                "low",
                                item.get("l", 0)
                            )
                        ),
                        close=float(
                            item.get(
                                "close",
                                item.get("c", 0)
                            )
                        ),
                        timestamp=item.get(
                            "timestamp",
                            item.get("time")
                        ),
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        return candles

    async def get_market_candles(
        self,
        market: str,
        symbol: str,
        timeframe: int = 60,
        count: int = 100,
    ) -> List[Candle]:

        normalized_market = market.upper()

        normalized_symbol = normalize_symbol(
            symbol
        )

        if normalized_market == "OTC":
            if not normalized_symbol.lower().endswith(
                "_otc"
            ):
                normalized_symbol += "_otc"

        elif normalized_market == "LIVE":
            if normalized_symbol.lower().endswith(
                "_otc"
            ):
                normalized_symbol = (
                    normalized_symbol[:-4]
                )

        else:
            raise ValueError(
                "market must be LIVE or OTC"
            )

        return await self.get_candles(
            symbol=normalized_symbol,
            timeframe=timeframe,
            count=count,
        )

    def is_connected(self) -> bool:
        return (
            self.connected
            and self.authenticated
        )

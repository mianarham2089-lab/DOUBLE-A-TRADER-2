import requests
from typing import List

from strategy import Candle


class QuotexMarketData:

    def __init__(self, api_url="http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")

    # ========================================================
    # GET ALL ACTIVE QUOTEX MARKETS
    # ========================================================

    def get_markets(self):

        url = f"{self.api_url}/api/v1/markets"

        response = requests.get(
            url,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        return data.get("data", [])

    # ========================================================
    # GET CANDLES
    # ========================================================

    def get_candles(
        self,
        symbol: str,
        limit: int = 100,
        include_running: bool = True,
    ) -> List[Candle]:

        url = f"{self.api_url}/api/v1/candles"

        params = {
            "symbol": symbol,
            "limit": limit,
            "timezone": "UTC",
            "include_running": str(
                include_running
            ).lower(),
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        candle_data = data.get(
            "candles",
            []
        )

        candles = []

        for item in candle_data:

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
                        timestamp=item.get(
                            "timestamp"
                        ),
                    )
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

        return candles

    # ========================================================
    # GET LIVE CANDLE
    # ========================================================

    def get_live_candle(
        self,
        symbol: str,
    ):

        url = f"{self.api_url}/api/v1/live"

        params = {
            "symbol": symbol,
            "timezone": "UTC",
        }

        response = requests.get(
            url,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    # ========================================================
    # API STATUS
    # ========================================================

    def status(self):

        try:

            response = requests.get(
                f"{self.api_url}/api/v1/markets",
                timeout=10
            )

            if response.ok:

                return {
                    "connected": True,
                    "provider": "Quotex",
                }

        except Exception:
            pass

        return {
            "connected": False,
            "provider": "Quotex",
        }

import os
from dataclasses import dataclass


@dataclass
class QuotexConfig:
    ssid: str = ""
    demo: bool = False

    websocket_timeout: int = 30
    reconnect_delay: int = 5

    persistent_connection: bool = True
    auto_reconnect: bool = True

    @classmethod
    def from_environment(cls):
        return cls(
            ssid=os.getenv("QUOTEX_SSID", ""),
            demo=os.getenv("QUOTEX_DEMO", "false").lower()
            in ("1", "true", "yes"),
        )

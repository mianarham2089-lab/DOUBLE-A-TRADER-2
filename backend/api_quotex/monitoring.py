import time
from typing import Any, Dict


class ConnectionMonitor:

    def __init__(self):
        self.connected = False
        self.last_update = 0
        self.last_error = ""

    def set_connected(self, value: bool):
        self.connected = bool(value)
        self.last_update = int(time.time())

        if self.connected:
            self.last_error = ""

    def set_error(self, error: Any):
        self.connected = False
        self.last_error = str(error)
        self.last_update = int(time.time())

    def status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "last_update": self.last_update,
            "last_error": self.last_error,
        }

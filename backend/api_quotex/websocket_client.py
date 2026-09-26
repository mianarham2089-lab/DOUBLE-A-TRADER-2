import asyncio
import json
from typing import Any, Callable, Optional


class QuotexWebSocket:

    def __init__(
        self,
        url: str = "",
        on_message: Optional[Callable] = None,
    ):
        self.url = url
        self.on_message = on_message

        self.websocket = None
        self.connected = False
        self.running = False

    async def connect(self):
        """
        WebSocket connection placeholder.

        The actual Quotex connection will be connected
        through the official client implementation.
        """
        self.running = True
        return False

    async def disconnect(self):
        self.running = False
        self.connected = False

        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass

            self.websocket = None

    async def send(self, data: Any):
        if not self.websocket:
            return False

        try:
            if isinstance(data, str):
                message = data
            else:
                message = json.dumps(data)

            await self.websocket.send(message)
            return True

        except Exception:
            return False

    async def receive_loop(self):
        while self.running and self.websocket:

            try:
                message = await self.websocket.recv()

                try:
                    message = json.loads(message)
                except Exception:
                    pass

                if self.on_message:
                    result = self.on_message(message)

                    if asyncio.iscoroutine(result):
                        await result

            except asyncio.CancelledError:
                break

            except Exception:
                self.connected = False
                break

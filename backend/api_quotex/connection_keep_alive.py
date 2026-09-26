import asyncio
from typing import Callable, Optional


class ConnectionKeepAlive:

    def __init__(
        self,
        ping_callback: Optional[Callable] = None,
        interval: int = 15,
    ):
        self.ping_callback = ping_callback
        self.interval = interval
        self.running = False
        self._task = None

    async def _loop(self):
        while self.running:
            try:
                if self.ping_callback:
                    result = self.ping_callback()

                    if asyncio.iscoroutine(result):
                        await result

            except Exception:
                pass

            await asyncio.sleep(self.interval)

    async def start(self):
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(
            self._loop()
        )

    async def stop(self):
        self.running = False

        if self._task:
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                pass

            self._task = None

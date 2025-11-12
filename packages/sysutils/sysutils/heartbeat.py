import asyncio
import logging

logger = logging.getLogger(__name__)


class HeartbeatMonitor:

    def __init__(self, heartbeat_func, notify_func):
        self._stop_event = asyncio.Event()
        self._monitor_task = None
        self._heartbeat_func = heartbeat_func
        self._notify_func = notify_func

    async def start(self, interval):
        if self._monitor_task is None:
            self._interval = interval
            self._monitor_task = asyncio.create_task(self._monitor())

    async def stop(self):
        if self._monitor_task is not None:
            self._stop_event.set()
            await self._monitor_task
            self._monitor_task = None

    async def _monitor(self):
        while not self._stop_event.is_set():
            logger.debug('will do heartbeat')
            try:
                if not await self._heartbeat_func():
                    await self._notify_func()
            except Exception as e:
                await self._notify_func()
                logger.error(f'心跳检测时发生错误: {e}')
            await asyncio.sleep(self._interval)

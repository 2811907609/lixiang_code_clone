import asyncio

import pytest
from sysutils.heartbeat import HeartbeatMonitor


@pytest.mark.asyncio
async def test_start_stop():
    # 创建简单的心跳和通知函数
    async def heartbeat():
        return True

    async def notify():
        pass

    monitor = HeartbeatMonitor(heartbeat, notify)
    await monitor.start(0.1)
    assert monitor._monitor_task is not None
    await monitor.stop()
    assert monitor._monitor_task is None


@pytest.mark.asyncio
async def test_heartbeat_failure():
    notify_count = 0

    # 创建总是失败的心跳函数
    async def heartbeat():
        return False

    # 创建计数的通知函数
    async def notify():
        nonlocal notify_count
        notify_count += 1

    monitor = HeartbeatMonitor(heartbeat, notify)
    await monitor.start(0.1)
    await asyncio.sleep(0.2)  # 等待两个心跳周期
    await monitor.stop()
    assert notify_count == 2  # 每次心跳失败都会触发通知


@pytest.mark.asyncio
async def test_heartbeat_error():
    notify_count = 0

    # 创建抛出异常的心跳函数
    async def heartbeat():
        raise Exception("Test error")

    # 创建计数的通知函数
    async def notify():
        nonlocal notify_count
        notify_count += 1

    monitor = HeartbeatMonitor(heartbeat, notify)
    await monitor.start(0.1)
    await asyncio.sleep(0.2)
    await monitor.stop()
    assert notify_count >= 1


@pytest.mark.asyncio
async def test_stop_without_start():
    # 创建简单的心跳和通知函数
    async def heartbeat():
        return True

    async def notify():
        pass

    monitor = HeartbeatMonitor(heartbeat, notify)
    assert monitor._monitor_task is None
    await monitor.stop()
    assert monitor._monitor_task is None

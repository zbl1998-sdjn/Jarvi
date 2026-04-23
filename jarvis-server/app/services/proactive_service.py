"""Proactive daemon: watches system metrics and pushes unsolicited
`proactive_speech` events to subscribed WebSocket clients.

Design constraints:
  * Zero impact when no client is connected (loop sleeps on empty fanout).
  * Each alert kind has a cooldown so Jarvis never spams.
  * Thresholds read from settings so they can be tuned without redeploy.
  * Import of `psutil` is lazy to keep unit tests runnable on minimal envs.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _AlertState:
    last_fired_at: float = 0.0


class ProactiveBus:
    """Fanout hub: WebSocket handlers subscribe with their send callable."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.discard(q)

    @property
    def has_subscribers(self) -> bool:
        return bool(self._subscribers)


@dataclass
class ProactiveConfig:
    cpu_threshold: float = 85.0
    mem_threshold: float = 90.0
    battery_threshold: int = 20
    disk_threshold: float = 92.0
    poll_seconds: float = 15.0
    cooldown_seconds: float = 300.0
    quiet_hours: tuple[int, int] = (0, 7)  # [start_hour, end_hour) in local time, silent

    def in_quiet_hours(self, now: float) -> bool:
        import datetime as _dt

        hour = _dt.datetime.fromtimestamp(now).hour
        start, end = self.quiet_hours
        if start == end:
            return False
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end


SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_CRITICAL = "critical"


def _cpu_severity(cpu: float) -> str:
    if cpu >= 97:
        return SEVERITY_CRITICAL
    if cpu >= 90:
        return SEVERITY_WARN
    return SEVERITY_INFO


def _mem_severity(mem: float) -> str:
    if mem >= 96:
        return SEVERITY_CRITICAL
    if mem >= 93:
        return SEVERITY_WARN
    return SEVERITY_INFO


def _battery_severity(pct: float) -> str:
    if pct <= 5:
        return SEVERITY_CRITICAL
    if pct <= 10:
        return SEVERITY_WARN
    return SEVERITY_INFO


@dataclass
class ProactiveDaemon:
    bus: ProactiveBus
    config: ProactiveConfig = field(default_factory=ProactiveConfig)
    _state: dict[str, _AlertState] = field(default_factory=dict)
    _task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="jarvis-proactive-daemon")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except (asyncio.CancelledError, Exception):
            pass
        self._task = None

    async def _run(self) -> None:
        try:
            import psutil  # noqa: F401 (lazy probe)
        except Exception:
            return
        while True:
            try:
                if self.bus.has_subscribers:
                    await self._check_once()
            except Exception:
                pass
            await asyncio.sleep(self.config.poll_seconds)

    async def _check_once(self) -> None:
        import psutil

        now = time.time()
        # Critical alerts bypass quiet hours; info/warn are suppressed.
        suppress_non_critical = self.config.in_quiet_hours(now)

        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        if cpu >= self.config.cpu_threshold and self._cooled("cpu", now):
            sev = _cpu_severity(cpu)
            if not (suppress_non_critical and sev != SEVERITY_CRITICAL):
                await self._fire(
                    "cpu",
                    f"先生，CPU 占用已达 {cpu:.0f}%，是否需要我排查后台进程？",
                    {"cpu": cpu},
                    sev,
                    now,
                )
        if mem >= self.config.mem_threshold and self._cooled("mem", now):
            sev = _mem_severity(mem)
            if not (suppress_non_critical and sev != SEVERITY_CRITICAL):
                await self._fire(
                    "mem",
                    f"先生，内存占用已达 {mem:.0f}%，建议关闭部分标签页。",
                    {"mem": mem},
                    sev,
                    now,
                )
        try:
            disk = psutil.disk_usage("C:\\" if _is_windows() else "/").percent
        except Exception:
            disk = 0.0
        if disk >= self.config.disk_threshold and self._cooled("disk", now):
            if not suppress_non_critical:
                await self._fire(
                    "disk",
                    f"先生，系统盘占用 {disk:.0f}%，建议清理一下。",
                    {"disk": disk},
                    SEVERITY_WARN,
                    now,
                )
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None
        if battery is not None and not battery.power_plugged:
            if battery.percent <= self.config.battery_threshold and self._cooled("battery", now):
                sev = _battery_severity(battery.percent)
                if not (suppress_non_critical and sev != SEVERITY_CRITICAL):
                    await self._fire(
                        "battery",
                        f"先生，电量只剩 {battery.percent:.0f}%，该接电源了。",
                        {"battery": battery.percent},
                        sev,
                        now,
                    )

    def _cooled(self, kind: str, now: float) -> bool:
        st = self._state.setdefault(kind, _AlertState())
        return now - st.last_fired_at >= self.config.cooldown_seconds

    async def _fire(
        self,
        kind: str,
        text: str,
        metrics: dict[str, float],
        severity: str,
        now: float,
    ) -> None:
        self._state.setdefault(kind, _AlertState()).last_fired_at = now
        await self.bus.publish(
            {
                "type": "proactive_speech",
                "kind": kind,
                "severity": severity,
                "text": text,
                "metrics": metrics,
            }
        )


def _is_windows() -> bool:
    import sys

    return sys.platform == "win32"


_BUS: ProactiveBus | None = None
_DAEMON: ProactiveDaemon | None = None


def get_bus() -> ProactiveBus:
    global _BUS
    if _BUS is None:
        _BUS = ProactiveBus()
    return _BUS


def get_daemon() -> ProactiveDaemon:
    global _DAEMON
    if _DAEMON is None:
        _DAEMON = ProactiveDaemon(bus=get_bus())
    return _DAEMON

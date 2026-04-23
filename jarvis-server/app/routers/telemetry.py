"""Telemetry ingress: external scripts (PowerShell profile, editor hooks, etc.)
push events here and we turn them into proactive speech events.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.proactive_service import get_bus

router = APIRouter()


class TerminalErrorPayload(BaseModel):
    command: str = ""
    exit_code: int = 1
    stderr_tail: str = ""
    cwd: str = ""
    shell: str = "powershell"


@router.post("/api/telemetry/terminal-error")
async def report_terminal_error(payload: TerminalErrorPayload) -> dict[str, Any]:
    """Accept a non-zero exit from a user's terminal and push a proactive alert."""
    bus = get_bus()
    cmd = payload.command.strip()[:160] or "(unknown command)"
    tail = payload.stderr_tail.strip().replace("\n", " ")[:240]
    text = f"先生，刚才在 {payload.shell} 里执行 `{cmd}` 失败（退出码 {payload.exit_code}）。"
    if tail:
        text += f" 末尾报错：{tail}"
    await bus.publish(
        {
            "type": "proactive_speech",
            "severity": "warn",
            "source": "terminal-hook",
            "text": text,
            "meta": {
                "command": cmd,
                "exit_code": payload.exit_code,
                "cwd": payload.cwd,
                "shell": payload.shell,
                "stderr_tail": tail,
            },
        }
    )
    return {"ok": True}

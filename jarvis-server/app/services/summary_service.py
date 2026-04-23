from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.kimi_client import KimiChatClient

_SOURCE_LABELS: dict[str, str] = {
    "file": "文件",
    "web": "网页",
    "session": "会话",
    "code": "代码",
    "search-results": "搜索结果",
    "workspace": "工作台",
    "voice": "语音",
}

MAX_CONTENT_CHARS = 8000

_SUMMARY_PROMPT_TEMPLATE = (
    "请对以下{source_label}内容进行总结，输出格式要求：\n"
    "第一行：一段简短的总结（一到两句话）。\n"
    "之后：3至5个要点，每行开头为减号加空格（格式如：- 要点内容）。\n\n"
    "内容：\n{content}"
)


def _parse_llm_response(response: str) -> tuple[str, list[str]]:
    bullets: list[str] = []
    summary_lines: list[str] = []
    for line in response.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("• "):
            bullets.append(stripped[2:].strip())
        elif stripped and not bullets:
            summary_lines.append(stripped)
    summary = " ".join(summary_lines)
    return summary, bullets


def _get_chat_client() -> KimiChatClient:
    from app.services.chat_service import create_chat_client
    return create_chat_client()


class SummaryService:
    def __init__(self, chat_client: KimiChatClient | None = None) -> None:
        self._chat_client = chat_client

    def summarize(self, source_type: str, content: str) -> dict[str, object]:
        client = self._chat_client or _get_chat_client()
        source_label = _SOURCE_LABELS.get(source_type, source_type)
        truncated = content[:MAX_CONTENT_CHARS]
        prompt = _SUMMARY_PROMPT_TEMPLATE.format(source_label=source_label, content=truncated)
        response = client.complete(query=prompt, history=[])
        summary, bullets = _parse_llm_response(response)
        return {"summary": summary, "bullets": bullets}

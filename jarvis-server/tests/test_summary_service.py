from app.services.summary_service import SummaryService


class FakeChatClient:
    """Deterministic fake for unit-testing SummaryService without a real LLM."""

    def __init__(self, response: str = "") -> None:
        self._response = response

    def complete(self, query: str, history: list, **kwargs) -> str:  # noqa: ARG002
        return self._response


_FAKE_LLM_RESPONSE = (
    "Jarvis 会话的核心内容是演示摘要能力。\n"
    "- Jarvis 支持搜索和总结\n"
    "- 会话记录了一段示例内容\n"
    "- 输出格式为结构化摘要\n"
)


def test_summarize_returns_reader_facing_summary_not_placeholder() -> None:
    """SummaryService must return real LLM text, not old placeholder metadata."""
    service = SummaryService(chat_client=FakeChatClient(_FAKE_LLM_RESPONSE))

    result = service.summarize("session", "Jarvis can summarize this session.")

    assert isinstance(result["summary"], str)
    assert result["summary"], "summary must be non-empty"
    assert isinstance(result["bullets"], list)
    assert len(result["bullets"]) > 0, "bullets list must not be empty"
    for bullet in result["bullets"]:
        assert not bullet.startswith("source="), f"placeholder bullet found: {bullet!r}"
        assert not bullet.startswith("label="), f"placeholder bullet found: {bullet!r}"
        assert not bullet.startswith("lines="), f"placeholder bullet found: {bullet!r}"
        assert not bullet.startswith("preview="), f"placeholder bullet found: {bullet!r}"


def test_summarize_bullets_parsed_from_llm_response() -> None:
    """Bullets must be extracted from the LLM response dash-list."""
    service = SummaryService(chat_client=FakeChatClient(_FAKE_LLM_RESPONSE))

    result = service.summarize("file", "some file content")

    assert "Jarvis 支持搜索和总结" in result["bullets"]
    assert "会话记录了一段示例内容" in result["bullets"]
    assert "输出格式为结构化摘要" in result["bullets"]


def test_summarize_summary_text_comes_from_llm_response() -> None:
    """The summary field must carry the LLM's prose, not a template string."""
    service = SummaryService(chat_client=FakeChatClient(_FAKE_LLM_RESPONSE))

    result = service.summarize("web", "some web content")

    assert "Jarvis 会话的核心内容是演示摘要能力" in result["summary"]


_BULLETS_ONLY_RESPONSE = (
    "- bullet one\n"
    "- bullet two\n"
    "- bullet three\n"
)


def test_parse_bullets_only_response_summary_not_raw_bullet() -> None:
    """When LLM returns bullets only (no prose preamble), summary must NOT be the raw first bullet line."""
    service = SummaryService(chat_client=FakeChatClient(_BULLETS_ONLY_RESPONSE))

    result = service.summarize("file", "some content")

    summary = result["summary"]
    assert isinstance(summary, str)
    assert not summary.startswith("- "), (
        f"summary must not be a raw bullet marker, got: {summary!r}"
    )
    assert "bullet one" in result["bullets"]
    assert "bullet two" in result["bullets"]


def test_summarize_truncates_large_content() -> None:
    """summarize() must truncate very large content before building the LLM prompt."""
    from app.services.summary_service import MAX_CONTENT_CHARS

    captured: list[str] = []

    class CapturingClient:
        def complete(self, query: str, history: list, **kwargs) -> str:  # noqa: ARG002
            captured.append(query)
            return "summary line\n- bullet one\n"

    oversized = "x" * (MAX_CONTENT_CHARS + 1000)
    service = SummaryService(chat_client=CapturingClient())
    service.summarize("file", oversized)

    assert captured, "complete() was never called"
    prompt = captured[0]
    content_section = prompt.split("内容：")[-1] if "内容：" in prompt else prompt
    assert len(content_section) <= MAX_CONTENT_CHARS + 50, (
        "prompt content section exceeds MAX_CONTENT_CHARS by too much"
    )

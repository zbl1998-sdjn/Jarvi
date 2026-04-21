from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class KimiChatClient:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    system_prompt: str

    def complete(
        self,
        query: str,
        history: list[tuple[str, str]],
        knowledge_context: str = "",
        teacher_style: str = "",
    ) -> str:
        if not self.api_key:
            raise RuntimeError("Kimi API key is not configured. Set KIMI_API_KEY before starting Jarvis.")

        response = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": self._build_messages(query, history, knowledge_context, teacher_style),
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        payload = response.json()
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("Kimi returned no choices.")

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            combined = "".join(part for part in text_parts if isinstance(part, str)).strip()
            if combined:
                return combined

        raise RuntimeError("Kimi returned an empty response.")

    def _build_messages(
        self,
        query: str,
        history: list[tuple[str, str]],
        knowledge_context: str,
        teacher_style: str,
    ) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        if teacher_style.strip():
            messages.append(
                {
                    "role": "system",
                    "content": f"当前老师风格：{teacher_style.strip()}。回复风格必须与该设定一致。",
                }
            )
        if knowledge_context.strip():
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "回答时优先参考以下学习资料片段；如果资料不足，请明确说明并给出最稳妥的下一步。\n\n"
                        f"{knowledge_context.strip()}"
                    ),
                }
            )
        messages.extend(
            {"role": role, "content": content}
            for role, content in history
            if role in {"user", "assistant", "system"} and content.strip()
        )
        messages.append({"role": "user", "content": query})
        return messages

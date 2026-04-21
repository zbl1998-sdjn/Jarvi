from dataclasses import asdict, dataclass
import re


WORKSPACE_KEYWORDS = {
    "search": ("search", "搜索", "search center"),
    "summary": ("summary", "总结", "summarize"),
    "records": ("records", "记录", "execution record"),
    "tasks": ("tasks", "任务", "timeline"),
}


@dataclass(frozen=True)
class ActionProposal:
    action_type: str
    target: str
    risk_level: str
    requires_confirmation: bool


@dataclass(frozen=True)
class Interpretation:
    heard_wakeword: bool
    normalized_text: str
    workspace: str | None = None
    clarification: str | None = None
    action_proposal: ActionProposal | None = None
    teacher_style: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.action_proposal is None:
            payload["action_proposal"] = None
        return payload


class WakewordService:
    def normalize(self, text: str) -> str:
        normalized = text.strip()
        replacements = {
            "jarviss": "Jarvis",
            "jarvice": "Jarvis",
            "贾维斯": "Jarvis",
            "佳维斯": "Jarvis",
            "github copilot": "GitHub Copilot",
            "read me": "README",
            "readme.md": "README.md",
            "type script": "TypeScript",
            "java script": "JavaScript",
            "power shell": "PowerShell",
            "d 盘": "D:\\",
            "c 盘": "C:\\",
        }

        for source, target in replacements.items():
            normalized = re.sub(source, lambda _match, value=target: value, normalized, flags=re.IGNORECASE)

        return normalized

    def heard_wakeword(self, text: str, hotkey_armed: bool) -> bool:
        if hotkey_armed:
            return True
        lowered = text.lower()
        return any(token in lowered for token in ("jarvis", "贾维斯", "佳维斯"))

    def interpret(self, text: str, hotkey_armed: bool = False) -> Interpretation:
        normalized = self.normalize(text)
        if not self.heard_wakeword(normalized, hotkey_armed):
          return Interpretation(
              heard_wakeword=False,
              normalized_text=normalized,
              clarification="请先说 Jarvis，或先用全局热键唤醒我。",
          )

        lowered = normalized.lower()
        if "高压陪练" in normalized or "面试高压" in normalized:
            return Interpretation(
                heard_wakeword=True,
                normalized_text=normalized,
                teacher_style="面试高压陪练型",
                clarification="已切换到面试高压陪练型老师风格。",
            )

        if "幽默风趣" in normalized or "轻松一点" in normalized:
            return Interpretation(
                heard_wakeword=True,
                normalized_text=normalized,
                teacher_style="幽默风趣型",
                clarification="已切换到幽默风趣型老师风格。",
            )

        for workspace, keywords in WORKSPACE_KEYWORDS.items():
            if any(keyword.lower() in lowered for keyword in keywords):
                return Interpretation(
                    heard_wakeword=True,
                    normalized_text=normalized,
                    workspace=workspace,
                )

        delete_match = re.search(r"(delete|删除)\s+(?P<target>.+)", normalized, flags=re.IGNORECASE)
        if delete_match:
            target = delete_match.group("target").strip()
            if any(token in target.lower() for token in ("something", "一下", "maybe", "某个", "some")):
                return Interpretation(
                    heard_wakeword=True,
                    normalized_text=normalized,
                    clarification="这是高风险模糊请求。请明确给出要删除的文件或目录完整路径，我才会继续。",
                )
            return Interpretation(
                heard_wakeword=True,
                normalized_text=normalized,
                action_proposal=ActionProposal(
                    action_type="delete_file",
                    target=target,
                    risk_level="dangerous",
                    requires_confirmation=True,
                ),
            )

        if "maybe" in lowered or "看一下" in normalized:
            return Interpretation(
                heard_wakeword=True,
                normalized_text=normalized,
                clarification="这是低风险模糊请求。你是要打开搜索中心，还是总结当前会话？",
            )

        return Interpretation(
            heard_wakeword=True,
            normalized_text=normalized,
            clarification="我已经听到你了，但还需要更具体一点的目标。",
        )

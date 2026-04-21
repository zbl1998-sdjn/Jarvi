from dataclasses import asdict, dataclass
from pathlib import Path
import re
import subprocess
import webbrowser

import httpx

from app.config import ROOT_DIR
from app.models import ActionAudit
from app.services.permission_service import PermissionService


@dataclass(frozen=True)
class ActionExecutionResult:
    action_type: str
    target: str
    risk_level: str
    requires_confirmation: bool
    status: str
    detail: str

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["output"] = self.detail
        return payload


class ActionService:
    def __init__(self, permission_service: PermissionService) -> None:
        self.permission_service = permission_service

    def propose(self, action_type: str, target: str) -> ActionExecutionResult:
        risk_level, requires_confirmation = self.permission_service.classify(
            action_type,
            target,
        )
        return ActionExecutionResult(
            action_type=action_type,
            target=target,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            status="proposed",
            detail="",
        )

    def execute(
        self,
        db,
        action_type: str,
        target: str,
        content: str | None = None,
        approved: bool = False,
    ) -> ActionExecutionResult:
        proposal = self.propose(action_type, target)
        if proposal.requires_confirmation and not approved:
            result = ActionExecutionResult(
                action_type=proposal.action_type,
                target=proposal.target,
                risk_level=proposal.risk_level,
                requires_confirmation=proposal.requires_confirmation,
                status="confirmation_required",
                detail="Action requires confirmation.",
            )
            self._audit(db, result)
            return result

        target_path = (ROOT_DIR / target).resolve() if not Path(target).is_absolute() else Path(target)
        detail = ""
        status = "completed"

        if action_type == "read_file":
            detail = target_path.read_text(encoding="utf-8")
        elif action_type == "write_file":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content or "", encoding="utf-8")
            detail = f"Wrote {target_path}"
        elif action_type == "run_command":
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", target],
                capture_output=True,
                text=True,
                check=False,
            )
            detail = completed.stdout.strip() or completed.stderr.strip()
            status = "completed" if completed.returncode == 0 else "failed"
        elif action_type == "fetch_web":
            detail = self._fetch_web_preview(target)
        elif action_type == "open_web_page":
            if not webbrowser.open(target):
                status = "failed"
                detail = f"Failed to open {target}"
            else:
                detail = f"Opened {target}"
        else:
            status = "failed"
            detail = f"Unsupported action: {action_type}"

        result = ActionExecutionResult(
            action_type=proposal.action_type,
            target=proposal.target,
            risk_level=proposal.risk_level,
            requires_confirmation=proposal.requires_confirmation,
            status=status,
            detail=detail,
        )
        self._audit(db, result)
        return result

    def _fetch_web_preview(self, target: str) -> str:
        response = httpx.get(target, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", response.text)
        condensed = " ".join(text.split())
        return condensed[:800] or target

    def _audit(self, db, result: ActionExecutionResult) -> None:
        db.add(
            ActionAudit(
                action_type=result.action_type,
                target=result.target,
                risk_level=result.risk_level,
                status=result.status,
                detail=result.detail,
            )
        )

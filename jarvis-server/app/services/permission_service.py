from pathlib import Path

from app.config import ROOT_DIR


class PermissionService:
    def classify(self, action_type: str, target: str) -> tuple[str, bool]:
        dangerous_actions = {"delete_file", "run_command", "open_web_page"}
        cautious_actions = {"fetch_web"}
        target_path = Path(target)
        is_outside_workspace = target_path.is_absolute() and ROOT_DIR not in target_path.parents and target_path != ROOT_DIR
        if action_type in dangerous_actions or is_outside_workspace:
            return ("dangerous", True)
        if action_type in cautious_actions:
            return ("normal", False)
        return ("normal", False)

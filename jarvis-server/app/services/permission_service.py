from pathlib import Path

from app.config import ROOT_DIR

# Actions whose target is a filesystem path that requires containment checking.
_FILE_ACTIONS: frozenset[str] = frozenset({"read_file", "write_file", "delete_file"})


class PermissionService:
    def __init__(self, workspace: Path = ROOT_DIR) -> None:
        self.workspace = workspace

    def classify(self, action_type: str, target: str) -> tuple[str, bool]:
        dangerous_actions = {"delete_file", "run_command", "open_web_page"}
        cautious_actions = {"fetch_web"}

        # Only run path-containment logic for filesystem actions.  Non-file
        # actions (e.g. fetch_web) carry URLs or commands, not file paths.
        is_outside_workspace = False
        if action_type in _FILE_ACTIONS:
            target_path = Path(target)
            if target_path.is_absolute():
                resolved = target_path.resolve()
            else:
                resolved = (self.workspace / target_path).resolve()

            workspace_resolved = self.workspace.resolve()
            try:
                resolved.relative_to(workspace_resolved)
            except ValueError:
                is_outside_workspace = True

        if action_type in dangerous_actions or is_outside_workspace:
            return ("dangerous", True)
        if action_type in cautious_actions:
            return ("normal", False)
        return ("normal", False)

"""Tests for Task 2: fix file action path traversal and approval credibility.

Key bugs fixed:
1. PermissionService.classify used raw relative input — ../../.env bypassed confirmation.
2. ActionService.propose/execute returned the raw unresolved target in result/audit.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import ROOT_DIR
from app.services.action_service import ActionService
from app.services.permission_service import PermissionService


class TestPermissionServiceRelativeTraversal:
    """PermissionService must resolve paths before deciding risk level."""

    def test_relative_traversal_read_requires_confirmation(self, tmp_path):
        """../../.env escapes workspace – must trigger confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("read_file", "../../.env")

        assert requires is True
        assert risk == "dangerous"

    def test_relative_traversal_write_requires_confirmation(self, tmp_path):
        """../../secret.txt escapes workspace for write – must require confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("write_file", "../../secret.txt")

        assert requires is True
        assert risk == "dangerous"

    def test_inside_workspace_relative_read_does_not_require_confirmation(self, tmp_path):
        """Relative path inside workspace must not trigger confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("read_file", "notes/todo.txt")

        assert requires is False
        assert risk == "normal"

    def test_absolute_outside_workspace_read_requires_confirmation(self, tmp_path):
        """Absolute path outside workspace must still require confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        outside = str(tmp_path / "outside.txt")
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("read_file", outside)

        assert requires is True
        assert risk == "dangerous"

    def test_absolute_inside_workspace_does_not_require_confirmation(self, tmp_path):
        """Absolute path inside workspace must not trigger confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        inside = str(workspace / "data.txt")
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("read_file", inside)

        assert requires is False
        assert risk == "normal"

    def test_default_workspace_is_root_dir(self):
        """PermissionService() with no args uses ROOT_DIR; ../../.env is outside it."""
        svc = PermissionService()

        risk, requires = svc.classify("read_file", "../../.env")

        assert requires is True
        assert risk == "dangerous"

    def test_dangerous_actions_always_require_confirmation(self, tmp_path):
        """dangerous action types are always dangerous regardless of path."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        inside = str(workspace / "cmd.txt")
        svc = PermissionService(workspace=workspace)

        for action in ("delete_file", "run_command", "open_web_page"):
            risk, requires = svc.classify(action, inside)
            assert requires is True, f"{action} should require confirmation"
            assert risk == "dangerous"

    def test_fetch_web_does_not_require_confirmation(self, tmp_path):
        """fetch_web is cautious but must not require confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        risk, requires = svc.classify("fetch_web", "https://example.com")

        assert requires is False
        assert risk == "normal"


class TestActionServiceResolvedTarget:
    """ActionService must use the resolved canonical path in proposals and audits."""

    def _make_service(self, workspace: Path) -> ActionService:
        return ActionService(
            permission_service=PermissionService(workspace=workspace),
        )

    def test_propose_uses_resolved_target_for_traversal(self, tmp_path):
        """propose() must return the resolved absolute path, not the raw traversal string."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)

        result = svc.propose("read_file", "../../.env")

        expected = str((workspace / "../../.env").resolve())
        assert result.target == expected
        assert result.requires_confirmation is True
        assert result.risk_level == "dangerous"

    def test_propose_requires_confirmation_for_relative_traversal(self, tmp_path):
        """propose() must set requires_confirmation=True for outside-workspace paths."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)

        result = svc.propose("read_file", "../../.env")

        assert result.requires_confirmation is True
        assert result.status == "proposed"

    def test_propose_inside_workspace_does_not_require_confirmation(self, tmp_path):
        """propose() for an inside-workspace path must not require confirmation."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)

        result = svc.propose("read_file", "notes/todo.txt")

        assert result.requires_confirmation is False
        assert result.target == str((workspace / "notes/todo.txt").resolve())

    def test_execute_confirmation_required_has_resolved_target(self, tmp_path):
        """execute() confirmation_required result must show the resolved path, not raw input."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)
        mock_db = MagicMock()

        result = svc.execute(mock_db, "read_file", "../../.env", approved=False)

        expected = str((workspace / "../../.env").resolve())
        assert result.status == "confirmation_required"
        assert result.target == expected

    def test_execute_audit_record_uses_resolved_target(self, tmp_path):
        """The audit record written to DB must contain the resolved target path."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)
        mock_db = MagicMock()

        svc.execute(mock_db, "read_file", "../../.env", approved=False)

        mock_db.add.assert_called_once()
        audit_arg = mock_db.add.call_args[0][0]
        expected = str((workspace / "../../.env").resolve())
        assert audit_arg.target == expected

    def test_execute_traversal_without_approval_is_blocked(self, tmp_path):
        """execute() without approval for outside-workspace read must return confirmation_required."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)
        mock_db = MagicMock()

        result = svc.execute(mock_db, "read_file", "../../.env", approved=False)

        assert result.status == "confirmation_required"
        assert result.requires_confirmation is True

    def test_execute_read_file_inside_workspace_completes(self, tmp_path):
        """execute() read_file inside workspace must complete and return resolved target."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "data.txt").write_text("hello content", encoding="utf-8")
        svc = self._make_service(workspace)
        mock_db = MagicMock()

        result = svc.execute(mock_db, "read_file", "data.txt")

        assert result.status == "completed"
        assert result.detail == "hello content"
        assert result.target == str((workspace / "data.txt").resolve())

    def test_execute_write_file_inside_workspace_completes(self, tmp_path):
        """execute() write_file inside workspace must complete and return resolved target."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = self._make_service(workspace)
        mock_db = MagicMock()

        result = svc.execute(mock_db, "write_file", "output.txt", content="written")

        assert result.status == "completed"
        assert (workspace / "output.txt").read_text(encoding="utf-8") == "written"
        assert result.target == str((workspace / "output.txt").resolve())

    def test_workspace_derived_from_permission_service(self, tmp_path):
        """ActionService.workspace must equal permission_service.workspace — single source of truth."""
        workspace = tmp_path / "ws"
        workspace.mkdir()
        ps = PermissionService(workspace=workspace)
        svc = ActionService(permission_service=ps)

        assert svc.workspace is ps.workspace


class TestPermissionServiceNonFileActions:
    """Path-containment logic must NOT run for non-filesystem action types."""

    def test_fetch_web_traversal_target_does_not_require_confirmation(self, tmp_path):
        """fetch_web with a traversal-like target must NOT trigger path containment."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        # A traversal string is meaningless for a URL action; the containment
        # guard must be skipped entirely, so the result stays normal/no-confirm.
        risk, requires = svc.classify("fetch_web", "../../.env")

        assert requires is False
        assert risk == "normal"

    def test_run_command_always_dangerous_regardless_of_target(self, tmp_path):
        """run_command is always dangerous; path containment is irrelevant to that verdict."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        svc = PermissionService(workspace=workspace)

        # Even a workspace-relative target must not slip through for run_command.
        risk, requires = svc.classify("run_command", "safe-looking-command")

        assert requires is True
        assert risk == "dangerous"

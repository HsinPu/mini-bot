"""Worktree sandbox inspection helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorktreeSandboxMetadata:
    enabled: bool
    status: str
    workspace_root: str
    repository_root: str | None = None
    base_branch: str | None = None
    base_commit: str | None = None
    reason: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "workspace_root": self.workspace_root,
            "repository_root": self.repository_root,
            "base_branch": self.base_branch,
            "base_commit": self.base_commit,
            "reason": self.reason,
        }


class WorktreeSandboxInspector:
    """Collect non-destructive git metadata for future isolated worktree runs."""

    def __init__(self, *, enabled: bool, workspace_root: Path):
        self.enabled = enabled
        self.workspace_root = Path(workspace_root).expanduser().resolve(strict=False)

    def inspect(self) -> WorktreeSandboxMetadata:
        if not self.enabled:
            return WorktreeSandboxMetadata(
                enabled=False,
                status="disabled",
                workspace_root=str(self.workspace_root),
                reason="worktree sandbox is disabled",
            )

        repository_root = self._git("rev-parse", "--show-toplevel")
        if repository_root is None:
            return WorktreeSandboxMetadata(
                enabled=True,
                status="unavailable",
                workspace_root=str(self.workspace_root),
                reason="workspace is not inside a git repository",
            )

        return WorktreeSandboxMetadata(
            enabled=True,
            status="ready",
            workspace_root=str(self.workspace_root),
            repository_root=repository_root,
            base_branch=self._git("rev-parse", "--abbrev-ref", "HEAD"),
            base_commit=self._git("rev-parse", "HEAD"),
        )

    def _git(self, *args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=self.workspace_root,
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

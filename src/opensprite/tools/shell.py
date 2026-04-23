"""Shell execution tool."""

import asyncio
import re
from pathlib import Path
from typing import Any, Callable

from .base import Tool
from .shell_runtime import (
    CapturedOutputChunk,
    drain_process_output,
    format_captured_output,
    start_shell_process,
)
from .validation import NON_EMPTY_STRING_PATTERN
from ..utils.processes import terminate_process_tree


WorkspaceResolver = Callable[[], Path]


def _resolve_workspace_root(workspace: Path) -> Path:
    """Resolve and ensure the workspace root directory exists."""
    root = Path(workspace).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_workspace_resolver(
    workspace: Path | None = None,
    workspace_resolver: WorkspaceResolver | None = None,
) -> WorkspaceResolver:
    """Build a normalized workspace resolver."""
    if workspace_resolver is not None:
        return lambda: _resolve_workspace_root(workspace_resolver())

    if workspace is None:
        raise ValueError("workspace or workspace_resolver is required")

    root = _resolve_workspace_root(workspace)
    return lambda: root


def _read_shell_token(command: str, start: int) -> tuple[str, int]:
    """Read one shell token, preserving quotes/escapes, starting at *start*."""
    i = start
    n = len(command)

    while i < n:
        ch = command[i]
        if ch.isspace() or ch in ";|&()":
            break
        if ch == "'":
            i += 1
            while i < n and command[i] != "'":
                i += 1
            if i < n:
                i += 1
            continue
        if ch == '"':
            i += 1
            while i < n:
                inner = command[i]
                if inner == "\\" and i + 1 < n:
                    i += 2
                    continue
                if inner == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "\\" and i + 1 < n:
            i += 2
            continue
        i += 1

    return command[start:i], i


def _has_shell_background_operator(command: str) -> bool:
    """Return True when the command uses shell backgrounding with `&`."""
    i = 0
    n = len(command)

    while i < n:
        ch = command[i]

        if ch.isspace():
            i += 1
            continue

        if ch == "#":
            nl = command.find("\n", i)
            if nl == -1:
                return False
            i = nl + 1
            continue

        if ch == "\\" and i + 1 < n:
            i += 2
            continue

        if ch in ("'", '"'):
            _, next_i = _read_shell_token(command, i)
            i = max(next_i, i + 1)
            continue

        if ch == "&":
            next_ch = command[i + 1] if i + 1 < n else ""
            if next_ch in {"&", ">"}:
                i += 2
                continue

            j = i - 1
            while j >= 0 and command[j].isspace():
                j -= 1
            if j >= 0 and command[j] in "<>":
                i += 1
                continue

            return True

        i += 1

    return False


# ---------------------------------------------------------------------------
# Foreground guardrails (aligned with hermes-agent terminal_tool policy)
# ---------------------------------------------------------------------------

_SHELL_LEVEL_BACKGROUND_RE = re.compile(r"\b(?:nohup|disown|setsid)\b", re.IGNORECASE)
_LONG_LIVED_FOREGROUND_PATTERNS = (
    re.compile(r"\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:dev|start|serve|watch)\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+compose\s+up\b", re.IGNORECASE),
    re.compile(r"\bnext\s+dev\b", re.IGNORECASE),
    re.compile(r"\bvite(?:\s|$)", re.IGNORECASE),
    re.compile(r"\bnodemon\b", re.IGNORECASE),
    re.compile(r"\buvicorn\b", re.IGNORECASE),
    re.compile(r"\bgunicorn\b", re.IGNORECASE),
    re.compile(r"\bpython(?:3)?\s+-m\s+http\.server\b", re.IGNORECASE),
)


def _looks_like_help_or_version_command(command: str) -> bool:
    """Return True for informational invocations that should never be blocked."""
    normalized = " ".join(command.lower().split())
    return (
        " --help" in normalized
        or normalized.endswith(" -h")
        or " --version" in normalized
        or normalized.endswith(" -v")
    )


def _foreground_exec_guidance(command: str) -> str | None:
    """Return a human-readable reason to refuse exec, or None if allowed."""
    if _looks_like_help_or_version_command(command):
        return None

    if _SHELL_LEVEL_BACKGROUND_RE.search(command):
        return (
            "exec cannot run commands that use nohup, disown, or setsid as shell-level "
            "background wrappers. Start long-lived processes outside exec (host service, "
            "tmux, systemd, or another terminal), then use exec only for short checks."
        )

    if _has_shell_background_operator(command):
        return (
            "exec cannot mix shell background '&' with this tool's captured stdout/stderr "
            "(the subprocess would hang or lose output). Start the server outside exec "
            "with logs redirected to a file, then run curl/tests in a separate exec call."
        )

    for pattern in _LONG_LIVED_FOREGROUND_PATTERNS:
        if pattern.search(command):
            return (
                "This command looks like it starts a long-lived dev server or watcher; "
                "exec is meant for short foreground commands. Start it outside OpenSprite, "
                "then verify with a separate short exec (curl, wget, etc.)."
            )

    return None


def _build_timeout_result(timeout: int, output: str, *, drained: bool) -> str:
    """Build the timeout response for exec output collection."""
    if not drained:
        output += (
            "\n\n[exec] Warning: output pipes did not close promptly after timeout; "
            "a descendant process may still have inherited stdout/stderr."
        )

    return (
        f"Error: Command timed out after {timeout}s. "
        "The command may be waiting for interactive input or may be stuck. "
        f"Partial output before timeout:\n{output}"
    )


def _build_pipe_drain_warning_result(output: str, *, drain_timeout: int) -> str:
    """Build the warning shown when output pipes stay open after exit."""
    return (
        f"{output}\n\n"
        f"[exec] Warning: output pipes did not close within {drain_timeout}s after "
        "the shell exited. A background process may still be writing to the same "
        "stdout/stderr as the shell. Redirect long-running servers to a file or "
        "/dev/null, or run them outside exec."
    )


class ExecTool(Tool):
    """Tool to execute shell commands."""

    MAX_COMMAND_LENGTH = 2000

    # Dangerous command patterns that are blocked
    DENY_PATTERNS = [
        r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf, rm -fr
        r"\bdel\s+/[fq]\b",              # del /f, del /q
        r"\berase\s+/(?:[fq]|qf)\b",     # erase /f, erase /q
        r"\brmdir\s+/s\b",               # rmdir /s
        r"\bremove-item\b.*(?:-recurse|-force)",  # powershell recursive delete
        r"\bgit\s+clean\b(?:[^\n]*\s)?-[^-\n]*f",  # git clean -f / -fd / -fdx
        r"\bgit\s+reset\s+--hard\b",    # destructive git reset
        r"(?:^|[;&|]\s*)format\b",       # format
        r"\b(mkfs|diskpart)\b",          # disk operations
        r"\bdd\s+if=",                   # dd
        r">\s*/dev/sd",                  # write to disk
        r"\b(shutdown|reboot|poweroff)\b",  # system power
        r":\(\)\s*\{.*\};\s*:",          # fork bomb
    ]

    def __init__(
        self,
        workspace: Path | None = None,
        *,
        workspace_resolver: WorkspaceResolver | None = None,
        timeout: int = 60,
        deny_patterns: list[str] | None = None,
    ):
        self._workspace_resolver = _build_workspace_resolver(workspace, workspace_resolver)
        self.timeout = timeout
        self.deny_patterns = deny_patterns or self.DENY_PATTERNS

    def _get_workspace(self) -> Path:
        return self._workspace_resolver()

    def _output_drain_timeout(self) -> int:
        return max(5, min(30, self.timeout))

    def _validate_command(self, command: str) -> str | None:
        for pattern in self.deny_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return "Error: Command blocked by safety guard (dangerous pattern detected)"

        if _looks_like_help_or_version_command(command):
            return None

        guidance = _foreground_exec_guidance(command)
        if guidance is not None:
            return f"Error: {guidance}"

        return None

    async def _handle_timed_out_process(
        self,
        process: asyncio.subprocess.Process,
        read_tasks: list[asyncio.Task[None]],
        output_chunks: list[CapturedOutputChunk],
    ) -> str:
        await terminate_process_tree(process)
        drained = await drain_process_output(
            read_tasks,
            timeout=self._output_drain_timeout(),
        )
        return _build_timeout_result(
            self.timeout,
            format_captured_output(output_chunks),
            drained=drained,
        )

    async def _handle_completed_process(
        self,
        read_tasks: list[asyncio.Task[None]],
        output_chunks: list[CapturedOutputChunk],
    ) -> str:
        drain_timeout = self._output_drain_timeout()
        drained = await drain_process_output(read_tasks, timeout=drain_timeout)
        output = format_captured_output(output_chunks)
        if not drained:
            return _build_pipe_drain_warning_result(output, drain_timeout=drain_timeout)
        return output

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return (
            "Execute one shell command inside the current workspace and return its output. "
            "Always provide a non-empty 'command' string containing the full command to run."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Required. Full shell command to execute inside the current workspace.",
                    "pattern": NON_EMPTY_STRING_PATTERN,
                    "maxLength": self.MAX_COMMAND_LENGTH,
                }
            },
            "required": ["command"]
        }

    async def _execute(self, **kwargs: Any) -> str:
        command = str(kwargs["command"]).strip()

        validation_error = self._validate_command(command)
        if validation_error is not None:
            return validation_error

        try:
            workspace = self._get_workspace()
            output_chunks: list[CapturedOutputChunk] = []
            process, read_tasks = await start_shell_process(
                command,
                cwd=str(workspace),
                output_chunks=output_chunks,
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=self.timeout)
            except asyncio.TimeoutError:
                return await self._handle_timed_out_process(process, read_tasks, output_chunks)

            return await self._handle_completed_process(read_tasks, output_chunks)
        except Exception as e:
            return f"Error executing command: {str(e)}"

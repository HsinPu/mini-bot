"""Update support for source-checkout OpenSprite installs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys


@dataclass(frozen=True)
class UpdateResult:
    """Summary of an OpenSprite update run."""

    project_root: Path
    branch: str
    before_rev: str
    after_rev: str
    updated: bool
    python_executable: Path


class UpdateError(RuntimeError):
    """Raised when OpenSprite cannot update safely."""


def find_project_root(start: Path | None = None) -> Path:
    """Find the repository root for the installed package."""
    current = Path(start or __file__).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / ".git").exists():
            return candidate
    raise UpdateError("OpenSprite is not installed from a git checkout; reinstall with scripts/install.sh.")


def find_python_executable(project_root: Path) -> Path:
    """Return the Python executable used for dependency installation."""
    candidates = [
        project_root / ".venv" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / "venv" / "bin" / "python",
        project_root / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _run(
    args: list[str],
    *,
    cwd: Path,
    runner=subprocess.run,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = runner(args, cwd=cwd, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        output = (result.stderr or result.stdout or "command failed").strip()
        raise UpdateError(output)
    return result


def _git_output(args: list[str], *, cwd: Path, runner=subprocess.run) -> str:
    return _run(["git", *args], cwd=cwd, runner=runner).stdout.strip()


def check_update_available(
    *,
    project_root: Path | None = None,
    branch: str = "main",
    runner=subprocess.run,
) -> int:
    """Fetch origin and return the number of commits behind origin/branch."""
    root = project_root or find_project_root()
    _run(["git", "fetch", "origin"], cwd=root, runner=runner)
    raw_count = _git_output(["rev-list", f"HEAD..origin/{branch}", "--count"], cwd=root, runner=runner)
    try:
        return int(raw_count)
    except ValueError as exc:
        raise UpdateError(f"Could not parse update count: {raw_count}") from exc


def update_checkout(
    *,
    project_root: Path | None = None,
    branch: str = "main",
    install_dev: bool = False,
    runner=subprocess.run,
) -> UpdateResult:
    """Fast-forward the checkout and reinstall the package into the local venv."""
    root = project_root or find_project_root()
    if not (root / ".git").exists():
        raise UpdateError("OpenSprite is not installed from a git checkout; reinstall with scripts/install.sh.")

    dirty = _git_output(["status", "--porcelain"], cwd=root, runner=runner)
    if dirty:
        raise UpdateError(
            "Local changes are present. Commit, stash, or discard them before running `opensprite update`."
        )

    before_rev = _git_output(["rev-parse", "HEAD"], cwd=root, runner=runner)
    _run(["git", "fetch", "origin"], cwd=root, runner=runner)
    _run(["git", "checkout", branch], cwd=root, runner=runner)

    count_raw = _git_output(["rev-list", f"HEAD..origin/{branch}", "--count"], cwd=root, runner=runner)
    try:
        commit_count = int(count_raw)
    except ValueError as exc:
        raise UpdateError(f"Could not parse update count: {count_raw}") from exc

    if commit_count:
        _run(["git", "pull", "--ff-only", "origin", branch], cwd=root, runner=runner)

    python_executable = find_python_executable(root)
    install_target = ".[dev]" if install_dev else "."
    _run([str(python_executable), "-m", "pip", "install", "--upgrade", "pip"], cwd=root, runner=runner)
    _run([str(python_executable), "-m", "pip", "install", "-e", install_target], cwd=root, runner=runner)

    after_rev = _git_output(["rev-parse", "HEAD"], cwd=root, runner=runner)
    return UpdateResult(
        project_root=root,
        branch=branch,
        before_rev=before_rev,
        after_rev=after_rev,
        updated=before_rev != after_rev,
        python_executable=python_executable,
    )

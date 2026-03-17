"""
minibot/workspace.py - 工作區輔助函式

提供以下功能：
- 取得工作區路徑（預設：~/.minibot）
- 從套件同步範本到工作區
- 載入啟動檔案（AGENTS.md、SOUL.md 等）
- 載入/儲存長期記憶（memory/MEMORY.md）
"""

import logging
import shutil
from pathlib import Path


MINIBOT_HOME = Path.home() / ".minibot"
LEGACY_WORKSPACE_DIR = MINIBOT_HOME / "workspace"
logger = logging.getLogger(__name__)


def get_workspace_path(workspace: str | None = None) -> Path:
    """Resolve and ensure workspace path. Defaults to ~/.minibot."""
    path = Path(workspace).expanduser() if workspace else MINIBOT_HOME
    path = ensure_dir(path)
    if workspace is None:
        migrate_legacy_workspace(path, silent=True)
    return path


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_default_workspace(path: Path) -> bool:
    """Return True when path points to the default ~/.minibot root."""
    return path.expanduser().resolve() == MINIBOT_HOME.resolve()


def _copy_missing_tree(source: Path, dest: Path, root: Path) -> list[str]:
    """Copy files from source to dest without overwriting existing files."""
    copied: list[str] = []

    if source.is_dir():
        dest.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            copied.extend(_copy_missing_tree(child, dest / child.name, root))
        return copied

    if dest.exists():
        return copied

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    try:
        copied.append(str(dest.relative_to(root)))
    except ValueError:
        copied.append(str(dest))
    return copied


def migrate_legacy_workspace(workspace: Path, silent: bool = False) -> list[str]:
    """Copy legacy ~/.minibot/workspace files into ~/.minibot without overwriting."""
    if not _is_default_workspace(workspace) or not LEGACY_WORKSPACE_DIR.exists():
        return []

    migrated: list[str] = []
    for item in LEGACY_WORKSPACE_DIR.iterdir():
        migrated.extend(_copy_missing_tree(item, workspace / item.name, workspace))

    if migrated and not silent:
        logger.info(f"Migrated legacy workspace files: {migrated}")

    return migrated


def sync_templates(workspace: Path, silent: bool = False) -> list[str]:
    """Sync bundled templates to workspace. Only creates missing files."""
    migrated = migrate_legacy_workspace(workspace, silent=silent)

    try:
        from importlib.resources import files as pkg_files
        tpl = pkg_files("minibot") / "templates"
    except Exception:
        return migrated
    
    if not tpl.is_dir():
        return migrated

    added: list[str] = list(migrated)

    def _write(src, dest: Path, track_relative: bool = True):
        if dest.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8") if src else "", encoding="utf-8")
        if track_relative:
            try:
                added.append(str(dest.relative_to(workspace)))
            except ValueError:
                # File is outside workspace, use absolute path
                added.append(str(dest))

    for item in tpl.iterdir():
        if item.name.endswith(".md"):
            _write(item, workspace / item.name)
    
    # Handle memory subdirectory
    memory_tpl = tpl / "memory"
    if memory_tpl.is_dir():
        memory_dir = workspace / "memory"
        memory_dir.mkdir(exist_ok=True)
        for item in memory_tpl.iterdir():
            if item.name.endswith(".md"):
                _write(item, memory_dir / item.name)

    # Sync default skills to ~/.minibot/skills/ (system-wide, not to workspace)
    default_skills_dir = Path.home() / ".minibot" / "skills"
    skills_tpl = pkg_files("minibot") / "skills"
    if skills_tpl.is_dir():
        default_skills_dir.mkdir(parents=True, exist_ok=True)
        for skill_folder in skills_tpl.iterdir():
            if not skill_folder.is_dir():
                continue
            skill_dest = default_skills_dir / skill_folder.name
            skill_dest.mkdir(parents=True, exist_ok=True)
            for item in skill_folder.iterdir():
                if item.name.endswith((".md", ".py")):
                    _write(item, skill_dest / item.name)

    if added and not silent:
        logger.info(f"Created template files: {added}")
    
    return added


# Bootstrap files to load
BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "IDENTITY.md", "TOOLS.md"]


def load_bootstrap_files(workspace: Path) -> dict[str, str]:
    """
    Load bootstrap files from workspace.
    
    Returns dict with filename (without .md) as key, content as value.
    Empty string if file doesn't exist.
    """
    result = {}
    for filename in BOOTSTRAP_FILES:
        file_path = workspace / filename
        if file_path.exists():
            result[filename.replace(".md", "")] = file_path.read_text(encoding="utf-8")
        else:
            result[filename.replace(".md", "")] = ""
    return result


def load_memory(workspace: Path) -> str:
    """
    Load long-term memory from workspace.
    
    Returns content of memory/MEMORY.md, or empty string if not found.
    """
    memory_path = workspace / "memory" / "MEMORY.md"
    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")
    return ""


def save_memory(workspace: Path, content: str) -> None:
    """
    Save long-term memory to workspace.
    
    Creates directory and file if needed.
    """
    memory_path = workspace / "memory" / "MEMORY.md"
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(content, encoding="utf-8")

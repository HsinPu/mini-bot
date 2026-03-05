"""Workspace helper functions."""

from pathlib import Path


def get_workspace_path(workspace: str | None = None) -> Path:
    """Resolve and ensure workspace path. Defaults to ~/.minibot/workspace."""
    path = Path(workspace).expanduser() if workspace else Path.home() / ".minibot" / "workspace"
    return ensure_dir(path)


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def sync_templates(workspace: Path, silent: bool = False) -> list[str]:
    """Sync bundled templates to workspace. Only creates missing files."""
    try:
        from importlib.resources import files as pkg_files
        tpl = pkg_files("minibot") / "templates"
    except Exception:
        return []
    
    if not tpl.is_dir():
        return []

    added: list[str] = []

    def _write(src, dest: Path):
        if dest.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(src.read_text(encoding="utf-8") if src else "", encoding="utf-8")
        added.append(str(dest.relative_to(workspace)))

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

    if added and not silent:
        print(f"Created template files: {added}")
    
    return added

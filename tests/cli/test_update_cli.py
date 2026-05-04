import subprocess

from typer.testing import CliRunner

from opensprite.cli.commands import app
from opensprite.cli import update as update_cli


runner = CliRunner()


def completed(args, stdout="", returncode=0):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr="")


def test_update_checkout_fast_forwards_and_reinstalls(tmp_path):
    root = tmp_path
    (root / ".git").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='opensprite'\n", encoding="utf-8")
    python_path = root / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("", encoding="utf-8")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["git", "status", "--porcelain"]:
            return completed(args, "")
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            rev = "before123" if calls.count(args) == 1 else "after456"
            return completed(args, rev + "\n")
        if args[:2] == ["git", "rev-list"]:
            return completed(args, "1\n")
        return completed(args, "")

    result = update_cli.update_checkout(project_root=root, runner=fake_run)

    assert result.updated is True
    assert result.before_rev == "before123"
    assert result.after_rev == "after456"
    assert ["git", "pull", "--ff-only", "origin", "main"] in calls
    assert [str(python_path), "-m", "pip", "install", "-e", "."] in calls


def test_update_checkout_refuses_dirty_worktree(tmp_path):
    root = tmp_path
    (root / ".git").mkdir()

    def fake_run(args, **kwargs):
        if args[:3] == ["git", "status", "--porcelain"]:
            return completed(args, " M README.md\n")
        return completed(args, "")

    try:
        update_cli.update_checkout(project_root=root, runner=fake_run)
    except update_cli.UpdateError as exc:
        assert "Local changes are present" in str(exc)
    else:
        raise AssertionError("Expected dirty worktree to fail")


def test_update_check_command_renders_available_count(monkeypatch):
    monkeypatch.setattr(
        "opensprite.cli.commands.update_cli.check_update_available",
        lambda branch="main": 2,
    )

    result = runner.invoke(app, ["update", "--check"])

    assert result.exit_code == 0
    assert "Update available: 2 commit(s) behind origin/main." in result.stdout


def test_update_command_renders_success(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "opensprite.cli.commands.update_cli.update_checkout",
        lambda branch="main", install_dev=False: update_cli.UpdateResult(
            project_root=tmp_path,
            branch=branch,
            before_rev="before123",
            after_rev="after456",
            updated=True,
            python_executable=tmp_path / ".venv" / "bin" / "python",
        ),
    )

    result = runner.invoke(app, ["update"])

    assert result.exit_code == 0
    assert "Updated before1 -> after45 on main." in result.stdout

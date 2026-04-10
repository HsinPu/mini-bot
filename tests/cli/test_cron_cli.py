import re

from typer.testing import CliRunner

from opensprite.cli.commands import app


runner = CliRunner()


def test_cron_cli_add_list_and_remove(monkeypatch, tmp_path):
    monkeypatch.setattr("opensprite.cli.commands._resolve_workspace_root", lambda: tmp_path / "workspace")

    add_result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--session",
            "telegram:user-a",
            "--message",
            "Check weather and report back",
            "--name",
            "weather-check",
            "--every-seconds",
            "300",
        ],
    )

    assert add_result.exit_code == 0
    assert "Created job 'weather-check'" in add_result.stdout
    job_id = re.search(r"id: ([a-f0-9]{8})", add_result.stdout)
    assert job_id is not None

    list_result = runner.invoke(app, ["cron", "list", "--session", "telegram:user-a"])
    assert list_result.exit_code == 0
    assert "Scheduled jobs:" in list_result.stdout
    assert "weather-check" in list_result.stdout
    assert "every 5m" in list_result.stdout

    remove_result = runner.invoke(
        app,
        ["cron", "remove", "--session", "telegram:user-a", "--job-id", job_id.group(1)],
    )
    assert remove_result.exit_code == 0
    assert f"Removed job {job_id.group(1)}" in remove_result.stdout

    empty_list = runner.invoke(app, ["cron", "list", "--session", "telegram:user-a"])
    assert empty_list.exit_code == 0
    assert empty_list.stdout.strip() == "No scheduled jobs."


def test_cron_cli_requires_exactly_one_schedule(monkeypatch, tmp_path):
    monkeypatch.setattr("opensprite.cli.commands._resolve_workspace_root", lambda: tmp_path / "workspace")

    result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--session",
            "telegram:user-a",
            "--message",
            "Bad schedule",
            "--every-seconds",
            "60",
            "--cron-expr",
            "0 9 * * *",
        ],
    )

    assert result.exit_code == 1
    assert "provide exactly one of --every-seconds, --cron-expr, or --at" in result.stderr


def test_cron_cli_can_pause_and_enable_job(monkeypatch, tmp_path):
    monkeypatch.setattr("opensprite.cli.commands._resolve_workspace_root", lambda: tmp_path / "workspace")

    add_result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--session",
            "telegram:user-a",
            "--message",
            "Check weather and report back",
            "--every-seconds",
            "300",
        ],
    )
    job_id = re.search(r"id: ([a-f0-9]{8})", add_result.stdout)
    assert job_id is not None

    pause_result = runner.invoke(
        app,
        ["cron", "pause", "--session", "telegram:user-a", "--job-id", job_id.group(1)],
    )
    assert pause_result.exit_code == 0
    assert f"Paused job {job_id.group(1)}" in pause_result.stdout

    enable_result = runner.invoke(
        app,
        ["cron", "enable", "--session", "telegram:user-a", "--job-id", job_id.group(1)],
    )
    assert enable_result.exit_code == 0
    assert f"Enabled job {job_id.group(1)}" in enable_result.stdout


def test_cron_cli_can_run_job_immediately(monkeypatch, tmp_path):
    monkeypatch.setattr("opensprite.cli.commands._resolve_workspace_root", lambda: tmp_path / "workspace")

    add_result = runner.invoke(
        app,
        [
            "cron",
            "add",
            "--session",
            "telegram:user-a",
            "--message",
            "Check weather and report back",
            "--every-seconds",
            "300",
        ],
    )
    job_id = re.search(r"id: ([a-f0-9]{8})", add_result.stdout)
    assert job_id is not None

    run_result = runner.invoke(
        app,
        ["cron", "run", "--session", "telegram:user-a", "--job-id", job_id.group(1)],
    )
    assert run_result.exit_code == 0
    assert f"Ran job {job_id.group(1)}" in run_result.stdout

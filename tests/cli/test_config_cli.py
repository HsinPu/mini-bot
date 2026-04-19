import json

from typer.testing import CliRunner

from opensprite.cli.commands import app


runner = CliRunner()


def _write_split_config(root):
    (root / "opensprite.json").write_text(
        json.dumps(
            {
                "llm": {
                    "providers_file": "llm.providers.json",
                    "default": "openai",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "storage": {"type": "memory", "path": "memory.db"},
                "channels_file": "channels.json",
                "search_file": "search.json",
                "media_file": "media.json",
                "log": {
                    "enabled": True,
                    "retention_days": 365,
                    "level": "INFO",
                    "log_system_prompt": True,
                    "log_system_prompt_lines": 0,
                },
                "tools": {"mcp_servers_file": "mcp_servers.json"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "llm.providers.json").write_text(
        json.dumps(
            {
                "openai": {
                    "api_key": "key",
                    "enabled": True,
                    "model": "gpt-4.1-mini",
                    "base_url": "https://api.openai.com/v1",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "channels.json").write_text(
        json.dumps({"telegram": {"enabled": False, "token": ""}, "console": {"enabled": True}}, indent=2),
        encoding="utf-8",
    )
    (root / "search.json").write_text(
        json.dumps(
            {
                "enabled": False,
                "history_top_k": 5,
                "knowledge_top_k": 5,
                "embedding": {
                    "enabled": False,
                    "provider": "openai",
                    "api_key": "",
                    "model": "",
                    "base_url": None,
                    "batch_size": 16,
                    "candidate_count": 20,
                    "candidate_strategy": "vector",
                    "vector_backend": "auto",
                    "vector_candidate_count": 50,
                    "retry_failed_on_startup": False,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "media.json").write_text(
        json.dumps(
            {
                "vision": {"enabled": False, "provider": "minimax", "api_key": "", "model": "", "base_url": None},
                "speech": {"enabled": False, "provider": "minimax", "api_key": "", "model": "", "base_url": None},
                "video": {"enabled": False, "provider": "minimax", "api_key": "", "model": "", "base_url": None},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "mcp_servers.json").write_text("{}\n", encoding="utf-8")
    return root / "opensprite.json"


def test_config_validate_reports_valid_split_config(tmp_path):
    config_path = _write_split_config(tmp_path)

    result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "OpenSprite Config Validation" in result.stdout
    assert "Valid: yes" in result.stdout
    assert "Enabled channels: console" in result.stdout
    assert "MCP servers: none" in result.stdout


def test_config_validate_reports_missing_external_file(tmp_path):
    config_path = _write_split_config(tmp_path)
    (tmp_path / "media.json").unlink()

    result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])

    assert result.exit_code == 1
    assert "Valid: no" in result.stdout
    assert "Missing config files: media" in result.stdout


def test_config_validate_json_output_includes_error_details(tmp_path):
    config_path = _write_split_config(tmp_path)
    (tmp_path / "search.json").write_text("[]", encoding="utf-8")

    result = runner.invoke(app, ["config", "validate", "--config", str(config_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["config_exists"] is True
    assert any(entry["name"] == "search" and entry["valid_json"] is False for entry in payload["files"])
    assert "JSON root must be an object" in payload["error"]

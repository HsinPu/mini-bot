import json
import asyncio

from opensprite.agent.tool_registration import register_config_tools
from opensprite.tools import ToolRegistry
from opensprite.tools.credential_store import CredentialStoreTool


def test_credential_store_tool_adds_without_leaking_secret(tmp_path):
    tool = CredentialStoreTool(app_home=tmp_path)

    result = asyncio.run(tool.execute(
        action="add",
        provider="openrouter",
        secret="router-secret",
        label="Router",
    ))

    payload = json.loads(result)
    credential = payload["credential"]
    store = json.loads((tmp_path / "auth.json").read_text(encoding="utf-8"))

    assert credential["id"].startswith("cred_")
    assert credential["secret_preview"] == "rout...cret"
    assert "secret" not in credential
    assert "router-secret" not in result
    assert store["credentials"]["openrouter"][0]["secret"] == "router-secret"


def test_credential_store_tool_lists_and_sets_default(tmp_path):
    tool = CredentialStoreTool(app_home=tmp_path)
    created = json.loads(asyncio.run(tool.execute(action="add", provider="openai", secret="openai-secret")))["credential"]

    default_result = asyncio.run(tool.execute(action="set_default", capability="llm.chat", credential_id=created["id"]))
    list_result = asyncio.run(tool.execute(action="list", provider="openai"))

    assert json.loads(default_result)["credential"]["id"] == created["id"]
    listed = json.loads(list_result)["credentials"]["openai"][0]
    assert listed["is_default"] is True
    assert "openai-secret" not in list_result


def test_tool_registry_sanitizes_credential_params_for_hooks(tmp_path):
    async def scenario():
        registry = ToolRegistry()
        registry.register(CredentialStoreTool(app_home=tmp_path))
        seen = []

        async def before_execute(name, params):
            seen.append((name, params))

        result = await registry.execute(
            "credential_store",
            {"action": "add", "provider": "openrouter", "secret": "router-secret"},
            on_before_execute=before_execute,
        )
        return result, seen

    result, seen = asyncio.run(scenario())

    assert json.loads(result)["credential"]["secret_preview"] == "rout...cret"
    assert seen == [("credential_store", {"action": "add", "provider": "openrouter", "secret": "***redacted***"})]


def test_register_config_tools_includes_credential_store(tmp_path):
    registry = ToolRegistry()

    async def reload_mcp():
        return "reloaded"

    register_config_tools(
        registry,
        config_path_resolver=lambda: tmp_path / "opensprite.json",
        reload_mcp=reload_mcp,
        app_home=tmp_path,
        workspace_resolver=lambda: tmp_path,
    )

    assert "credential_store" in registry.tool_names

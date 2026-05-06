import asyncio

from opensprite import runtime
from opensprite.config import Config
from opensprite.llms import UnconfiguredLLM


def test_create_agent_uses_fallback_llm_when_unconfigured(tmp_path):
    config_path = tmp_path / "opensprite.json"
    Config.copy_template(config_path)
    config = Config.from_json(config_path)

    assert config.is_llm_configured is False

    agent, mq, cron_manager = asyncio.run(runtime.create_agent(config))

    try:
        assert isinstance(agent.provider, UnconfiguredLLM)
        assert agent.llm_configured is False
        assert mq is not None
        assert cron_manager is not None
    finally:
        asyncio.run(agent.close_background_maintenance())
        asyncio.run(agent.close_background_skill_reviews())
        asyncio.run(agent.close_background_processes())

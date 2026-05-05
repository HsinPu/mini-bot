import asyncio
from types import SimpleNamespace

from opensprite.agent.message_history import MessageHistoryService
from opensprite.llms import ChatMessage
from opensprite.llms.minimax import MiniMaxLLM
from opensprite.storage import MemoryStorage, StoredMessage


def test_minimax_chat_enables_reasoning_split_and_preserves_history_details():
    calls = []

    class FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                id="response-id",
                model="MiniMax-M2.7",
                object="chat.completion",
                usage=None,
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content="final answer",
                            tool_calls=None,
                            reasoning_details=[{"type": "reasoning.text", "text": "thinking"}],
                        ),
                    )
                ],
            )

    provider = MiniMaxLLM(api_key="secret-key", default_model="MiniMax-M2.7")
    provider.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    response = asyncio.run(
        provider.chat(
            [
                ChatMessage(
                    role="assistant",
                    content="previous answer",
                    reasoning_details=[{"type": "reasoning.text", "text": "previous thinking"}],
                ),
                ChatMessage(role="user", content="continue"),
            ]
        )
    )

    assert response.content == "final answer"
    assert response.reasoning_details == [{"type": "reasoning.text", "text": "thinking"}]
    assert calls[0]["extra_body"] == {"reasoning_split": True}
    assert calls[0]["messages"][0]["reasoning_details"] == [
        {"type": "reasoning.text", "text": "previous thinking"}
    ]


def test_message_history_restores_reasoning_details_from_metadata():
    storage = MemoryStorage()
    asyncio.run(
        storage.add_message(
            "session-1",
            StoredMessage(
                role="assistant",
                content="final answer",
                timestamp=1,
                metadata={"llm_reasoning_details": [{"type": "reasoning.text", "text": "thinking"}]},
            ),
        )
    )
    service = MessageHistoryService(storage=storage, search_store=None, max_history_getter=lambda: 10)

    history = asyncio.run(service.load_history("session-1"))

    assert history == [
        ChatMessage(
            role="assistant",
            content="final answer",
            reasoning_details=[{"type": "reasoning.text", "text": "thinking"}],
        )
    ]

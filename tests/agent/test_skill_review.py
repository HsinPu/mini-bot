from opensprite.agent.skill_review import build_skill_review_user_content, format_stored_messages_for_transcript
from opensprite.storage.base import StoredMessage


def test_format_stored_messages_for_transcript_includes_tool_name():
    rows = [
        StoredMessage(role="user", content="hi", timestamp=1.0),
        StoredMessage(role="assistant", content="hello", timestamp=2.0),
        StoredMessage(role="tool", content="output", timestamp=3.0, tool_name="read_file"),
    ]
    text = format_stored_messages_for_transcript(rows)
    assert "USER" in text
    assert "ASSISTANT" in text
    assert "[tool:read_file]" in text
    assert "output" in text


def test_build_skill_review_user_content_wraps_transcript():
    body = build_skill_review_user_content("LINE1")
    assert "--- TRANSCRIPT ---" in body
    assert "LINE1" in body
    assert "Nothing to save" in body

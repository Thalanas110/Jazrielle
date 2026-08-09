import pytest

from app.modules.assistant.intent import IntentParseError, parse_intent


def test_parse_intent_accepts_canonical_json():
    intent = parse_intent('{"action":"get_time","arguments":{},"message":"Checking the time."}')

    assert intent.action == "get_time"
    assert intent.arguments == {}
    assert intent.message == "Checking the time."


def test_parse_intent_accepts_a_json_code_fence():
    intent = parse_intent('```json\n{"action":"conversation","arguments":{},"message":"Hello."}\n```')

    assert intent.action == "conversation"


def test_parse_intent_treats_plain_text_as_safe_conversation():
    intent = parse_intent("I'm running normally. What do you need?")

    assert intent.action == "conversation"
    assert intent.arguments == {}
    assert intent.message == "I'm running normally. What do you need?"


def test_parse_intent_removes_classifier_prefix_from_plain_conversation():
    intent = parse_intent(
        'conversation "I\'m Jazrielle, a lightweight personal desktop assistant running on Windows."'
    )

    assert intent.action == "conversation"
    assert intent.message == "I'm Jazrielle, a lightweight personal desktop assistant running on Windows."


@pytest.mark.parametrize(
    "response",
    [
        "",
        '{"action":"not_allowed","arguments":{},"message":"x"}',
        '{"action":"get_time","arguments":{},"message":""}',
    ],
)
def test_parse_intent_rejects_invalid_model_output(response: str):
    with pytest.raises(IntentParseError):
        parse_intent(response)

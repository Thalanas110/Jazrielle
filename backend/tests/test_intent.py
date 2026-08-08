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


@pytest.mark.parametrize(
    "response",
    [
        "not json",
        '{"action":"not_allowed","arguments":{},"message":"x"}',
        '{"action":"get_time","arguments":{},"message":""}',
    ],
)
def test_parse_intent_rejects_invalid_model_output(response: str):
    with pytest.raises(IntentParseError):
        parse_intent(response)

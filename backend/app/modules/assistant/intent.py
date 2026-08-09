import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


ActionName = Literal[
    "open_application",
    "close_application",
    "get_system_status",
    "get_cpu_usage",
    "get_memory_usage",
    "get_top_processes",
    "get_time",
    "get_date",
    "get_weather",
    "play_media",
    "pause_media",
    "set_volume",
    "create_reminder",
    "list_reminders",
    "get_updates",
    "start_project",
    "stop_project",
    "git_status",
    "open_url",
    "conversation",
]


class AssistantIntent(BaseModel):
    action: ActionName
    arguments: dict[str, Any] = Field(default_factory=dict)
    message: str = Field(min_length=1)


class IntentParseError(ValueError):
    """Raised when the model does not return a valid assistant intent."""


_CODE_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)


def parse_intent(response: str) -> AssistantIntent:
    candidate = response.strip()
    fenced = _CODE_FENCE_PATTERN.match(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        payload = json.loads(candidate)
        return AssistantIntent.model_validate(payload)
    except json.JSONDecodeError as error:
        if candidate:
            return AssistantIntent(action="conversation", arguments={}, message=candidate)
        raise IntentParseError("The model returned an invalid assistant intent.") from error
    except (TypeError, ValidationError) as error:
        raise IntentParseError("The model returned an invalid assistant intent.") from error

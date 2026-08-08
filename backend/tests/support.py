from app.modules.assistant.intent import AssistantIntent


def intent(action: str, arguments: dict | None = None, message: str = "Checking.") -> AssistantIntent:
    return AssistantIntent(action=action, arguments=arguments or {}, message=message)

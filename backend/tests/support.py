from app.modules.assistant.intent import AssistantIntent


class FakeSearchProvider:
    def __init__(self, results):
        self.results = results
        self.query = None

    def search(self, query: str):
        self.query = query
        return self.results


def intent(action: str, arguments: dict | None = None, message: str = "Checking.") -> AssistantIntent:
    return AssistantIntent(action=action, arguments=arguments or {}, message=message)

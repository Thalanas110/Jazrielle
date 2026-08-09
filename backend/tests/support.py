from app.modules.assistant.intent import AssistantIntent


class FakeSearchProvider:
    def __init__(self, results):
        self.results = results
        self.query = None

    def search(self, query: str):
        self.query = query
        return self.results


class FakeFetchProvider:
    def __init__(self, pages):
        self.pages = pages
        self.urls = None
        self.purpose = None

    def fetch(self, urls: list[str], purpose: str):
        self.urls = urls
        self.purpose = purpose
        return self.pages


def intent(action: str, arguments: dict | None = None, message: str = "Checking.") -> AssistantIntent:
    return AssistantIntent(action=action, arguments=arguments or {}, message=message)

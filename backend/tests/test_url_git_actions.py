from pathlib import Path
from types import SimpleNamespace

from app.modules.assistant.action_config import AssistantActionConfig
from app.modules.assistant.action_registry import build_action_registry
from tests.support import intent


class FakeGitAdapter:
    def __init__(self, output: str):
        self.output = output
        self.repository = None

    def status(self, repository: Path) -> str:
        self.repository = repository
        return self.output


def test_open_url_rejects_non_web_schemes():
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main")),
    ).execute(intent("open_url", {"url": "file:///secret.txt"}))

    assert result.handled is False
    assert result.launchUrl is None


def test_open_url_returns_validated_web_url():
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main")),
    ).execute(intent("open_url", {"url": "https://example.com/help"}))

    assert result.handled is True
    assert result.launchUrl == "https://example.com/help"


def test_git_status_uses_configured_repository_and_fixed_adapter():
    repository = Path("C:/repo").resolve()
    git = FakeGitAdapter("## main")
    config = AssistantActionConfig(settings={"repositoryPath": str(repository)})
    result = build_action_registry(config, SimpleNamespace(git=git)).execute(intent("git_status"))

    assert result.handled is True
    assert result.message == "## main"
    assert git.repository == repository

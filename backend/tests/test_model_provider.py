import asyncio

from app.modules.assistant.model.errors import ModelNotConfiguredError
from app.modules.assistant.model.providers.llama_cpp import LlamaCppProvider
from app.modules.assistant.model.types import ModelStatus
from app.modules.assistant.model.unavailable import UnavailableModelProvider


def test_unavailable_provider_reports_not_configured():
    provider = UnavailableModelProvider()

    assert provider.status() == ModelStatus(configured=False, ready=False)


def test_llama_provider_reports_missing_model_as_unconfigured(tmp_path):
    provider = LlamaCppProvider(tmp_path / "missing.gguf")

    assert provider.status() == ModelStatus(configured=False, ready=False)


def test_llama_provider_loads_lazily_and_returns_chat_content(tmp_path):
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"test")

    class FakeLlama:
        def create_chat_completion(self, **kwargs):
            assert kwargs["messages"][-1] == {"role": "user", "content": "hello"}
            return {"choices": [{"message": {"content": "<think>private reasoning</think>\n\nhello back"}}]}

    load_count = 0

    def factory(**kwargs):
        nonlocal load_count
        load_count += 1
        return FakeLlama()

    provider = LlamaCppProvider(model_path, model_factory=factory)

    assert provider.status() == ModelStatus(configured=True, ready=False)
    model, response = asyncio.run(provider.generate("hello", "be brief"))

    assert model == "qwen3-0.6b-q4_k_m"
    assert response == "hello back"
    assert load_count == 1


def test_llama_provider_raises_for_missing_model(tmp_path):
    provider = LlamaCppProvider(tmp_path / "missing.gguf")

    try:
        asyncio.run(provider.generate("hello", ""))
    except ModelNotConfiguredError:
        pass
    else:
        raise AssertionError("Expected ModelNotConfiguredError")

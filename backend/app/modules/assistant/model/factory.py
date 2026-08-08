from pathlib import Path

from app.modules.assistant.model.protocol import ModelProvider
from app.modules.assistant.model.providers.llama_cpp import LlamaCppProvider
from app.modules.assistant.model.unavailable import UnavailableModelProvider


def build_model_provider(model_path: Path, context_size: int, max_tokens: int) -> ModelProvider:
    if not model_path.is_file():
        return UnavailableModelProvider()
    return LlamaCppProvider(model_path, context_size=context_size, max_tokens=max_tokens)

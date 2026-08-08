import asyncio
import importlib.util
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.modules.assistant.model.errors import ModelNotConfiguredError, ModelRuntimeUnavailableError
from app.modules.assistant.model.output import clean_chat_response
from app.modules.assistant.model.types import ModelStatus


class LlamaCppProvider:
    def __init__(
        self,
        model_path: Path,
        *,
        context_size: int = 4096,
        max_tokens: int = 512,
        model_factory: Callable[..., Any] | None = None,
    ):
        self._model_path = model_path
        self._context_size = context_size
        self._max_tokens = max_tokens
        self._model_factory = model_factory
        self._model: Any | None = None
        self._load_lock = threading.Lock()
        self._generation_lock = asyncio.Lock()

    def status(self) -> ModelStatus:
        configured = self._model_path.is_file() and self._runtime_available()
        return ModelStatus(configured=configured, ready=configured and self._model is not None)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        if not self._model_path.is_file():
            raise ModelNotConfiguredError
        if not self._runtime_available():
            raise ModelRuntimeUnavailableError

        async with self._generation_lock:
            return await asyncio.to_thread(self._generate_sync, prompt, system)

    def _runtime_available(self) -> bool:
        return self._model_factory is not None or importlib.util.find_spec("llama_cpp") is not None

    def _generate_sync(self, prompt: str, system: str) -> tuple[str | None, str]:
        model = self._get_model()
        messages = []
        if system.strip():
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        result = model.create_chat_completion(
            messages=messages,
            max_tokens=self._max_tokens,
            temperature=0.7,
        )
        content = result["choices"][0]["message"]["content"]
        return "qwen3-0.6b-q4_k_m", clean_chat_response(content)

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is None:
                self._model = self._create_model()
        return self._model

    def _create_model(self) -> Any:
        factory = self._model_factory
        if factory is None:
            from llama_cpp import Llama

            factory = Llama
        return factory(
            model_path=str(self._model_path),
            n_ctx=self._context_size,
            verbose=False,
        )

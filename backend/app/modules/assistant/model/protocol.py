from typing import Protocol

from app.modules.assistant.model.types import ModelStatus


class ModelProvider(Protocol):
    def status(self) -> ModelStatus: ...

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]: ...

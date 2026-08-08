from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelStatus:
    configured: bool
    ready: bool


class ModelNotConfiguredError(RuntimeError):
    """Raised when inference is requested before a local model is configured."""


class ModelProvider(Protocol):
    def status(self) -> ModelStatus: ...

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]: ...


class UnavailableModelProvider:
    def status(self) -> ModelStatus:
        return ModelStatus(configured=False, ready=False)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        raise ModelNotConfiguredError

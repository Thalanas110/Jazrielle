from app.modules.assistant.model.errors import ModelNotConfiguredError
from app.modules.assistant.model.types import ModelStatus


class UnavailableModelProvider:
    def status(self) -> ModelStatus:
        return ModelStatus(configured=False, ready=False)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        raise ModelNotConfiguredError

from app.modules.assistant.commands import execute_command, get_capabilities
from app.modules.assistant.model import ModelProvider
from app.modules.assistant.schemas import CapabilitiesResponse, CommandResult, InferenceResult


class AssistantService:
    def __init__(self, model_provider: ModelProvider):
        self._model_provider = model_provider

    def get_capabilities(self) -> CapabilitiesResponse:
        return CapabilitiesResponse(
            assistant="JAZRIELLE",
            localMode=True,
            llmConfigured=self._model_provider.status().configured,
            capabilities=get_capabilities(),
        )

    def execute_command(self, command: str) -> CommandResult:
        return execute_command(command)

    async def generate_inference(self, prompt: str, system: str) -> InferenceResult:
        model, response = await self._model_provider.generate(prompt, system)
        return InferenceResult(model=model, response=response)

from app.modules.assistant.action_registry import ActionRegistry
from app.modules.assistant.commands import execute_command, get_capabilities
from app.modules.assistant.intent import parse_intent
from app.modules.assistant.model import ModelProvider
from app.modules.assistant.schemas import CapabilitiesResponse, CommandResult, InferenceResult


class AssistantService:
    def __init__(
        self,
        model_provider: ModelProvider,
        system_prompt: str,
        action_registry: ActionRegistry | None = None,
    ):
        self._model_provider = model_provider
        self._system_prompt = system_prompt
        self._action_registry = action_registry

    def get_capabilities(self) -> CapabilitiesResponse:
        return CapabilitiesResponse(
            assistant="JAZRIELLE",
            localMode=True,
            llmConfigured=self._model_provider.status().configured,
            capabilities=(
                self._action_registry.get_capabilities()
                if self._action_registry is not None
                else get_capabilities()
            ),
        )

    async def execute_command(self, command: str) -> CommandResult:
        if self._action_registry is None:
            return execute_command(command)
        _, response = await self._model_provider.generate(command, self._system_prompt)
        return self._action_registry.execute(parse_intent(response))

    async def generate_inference(self, prompt: str) -> InferenceResult:
        model, response = await self._model_provider.generate(prompt, self._system_prompt)
        return InferenceResult(model=model, response=response)

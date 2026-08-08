from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.commands import Capability, CommandResult, execute_command, get_capabilities
from app.services.model import ModelNotConfiguredError, ModelProvider


class CapabilitiesResponse(BaseModel):
    assistant: str
    localMode: bool
    llmConfigured: bool
    capabilities: list[Capability]


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class InferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    system: str = Field(default="", max_length=10_000)


class InferenceResult(BaseModel):
    model: str | None = None
    response: str


def build_jarvis_router(model_provider: ModelProvider) -> APIRouter:
    router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])

    @router.get("/capabilities", response_model=CapabilitiesResponse)
    async def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse(
            assistant="KAELITH",
            localMode=True,
            llmConfigured=model_provider.status().configured,
            capabilities=get_capabilities(),
        )

    @router.post("/execute", response_model=CommandResult)
    async def execute(payload: CommandRequest) -> CommandResult:
        return execute_command(payload.command)

    @router.post("/inference", response_model=InferenceResult)
    async def inference(payload: InferenceRequest) -> InferenceResult:
        try:
            model, response = await model_provider.generate(payload.prompt, payload.system)
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_CONFIGURED",
                    "message": "A local language model is not configured.",
                },
            ) from error
        return InferenceResult(model=model, response=response)

    return router

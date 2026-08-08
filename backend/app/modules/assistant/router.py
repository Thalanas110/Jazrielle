from fastapi import APIRouter, HTTPException

from app.modules.assistant.model import ModelNotConfiguredError
from app.modules.assistant.schemas import (
    CapabilitiesResponse,
    CommandRequest,
    CommandResult,
    InferenceRequest,
    InferenceResult,
)
from app.modules.assistant.service import AssistantService


def build_assistant_router(assistant_service: AssistantService) -> APIRouter:
    router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])

    @router.get("/capabilities", response_model=CapabilitiesResponse)
    async def capabilities() -> CapabilitiesResponse:
        return assistant_service.get_capabilities()

    @router.post("/execute", response_model=CommandResult)
    async def execute(payload: CommandRequest) -> CommandResult:
        return assistant_service.execute_command(payload.command)

    @router.post("/inference", response_model=InferenceResult)
    async def inference(payload: InferenceRequest) -> InferenceResult:
        try:
            return await assistant_service.generate_inference(payload.prompt, payload.system)
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_CONFIGURED",
                    "message": "A local language model is not configured.",
                },
            ) from error

    return router

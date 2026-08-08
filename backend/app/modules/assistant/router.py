from fastapi import APIRouter, HTTPException

from app.modules.assistant.action_registry import UnknownActionError
from app.modules.assistant.intent import IntentParseError
from app.modules.assistant.model import ModelNotConfiguredError, ModelRuntimeUnavailableError
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
        try:
            return await assistant_service.execute_command(payload.command)
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_CONFIGURED",
                    "message": "A local language model is not configured.",
                },
            ) from error
        except ModelRuntimeUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_RUNTIME_UNAVAILABLE",
                    "message": "The local language model runtime is not available.",
                },
            ) from error
        except IntentParseError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_MODEL_INTENT",
                    "message": "I couldn't understand that request.",
                },
            ) from error
        except UnknownActionError as error:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "UNSUPPORTED_ACTION",
                    "message": "That action is not available.",
                },
            ) from error

    @router.post("/inference", response_model=InferenceResult)
    async def inference(payload: InferenceRequest) -> InferenceResult:
        try:
            return await assistant_service.generate_inference(payload.prompt)
        except ModelNotConfiguredError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_NOT_CONFIGURED",
                    "message": "A local language model is not configured.",
                },
            ) from error
        except ModelRuntimeUnavailableError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "MODEL_RUNTIME_UNAVAILABLE",
                    "message": "The local language model runtime is not available.",
                },
            ) from error

    return router

from fastapi import APIRouter

from app.modules.assistant.model import ModelProvider
from app.modules.health.schemas import HealthResponse, ReadyResponse


def build_health_router(model_provider: ModelProvider) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @router.get("/ready", response_model=ReadyResponse)
    async def ready() -> ReadyResponse:
        return ReadyResponse(status="ok", model_configured=model_provider.status().configured)

    return router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import build_health_router
from app.api.jarvis import build_jarvis_router
from app.core.config import Settings, get_settings
from app.services.model import ModelProvider, UnavailableModelProvider


def create_app(
    settings: Settings | None = None,
    model_provider: ModelProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    resolved_provider = model_provider or UnavailableModelProvider()
    application = FastAPI(title=resolved_settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(build_health_router(resolved_provider))
    application.include_router(build_jarvis_router(resolved_provider))
    application.state.model_provider = resolved_provider
    return application


app = create_app()

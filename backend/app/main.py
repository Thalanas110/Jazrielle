from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, get_settings
from app.core.system_prompt import load_system_prompt
from app.modules.assistant.model import ModelProvider, build_model_provider
from app.modules.assistant.router import build_assistant_router
from app.modules.assistant.service import AssistantService
from app.modules.health.router import build_health_router


def create_app(
    settings: Settings | None = None,
    model_provider: ModelProvider | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    system_prompt = load_system_prompt(Path(resolved_settings.system_prompt_path))
    resolved_provider = model_provider or build_model_provider(
        Path(resolved_settings.model_path),
        context_size=resolved_settings.model_context_size,
        max_tokens=resolved_settings.model_max_tokens,
    )
    application = FastAPI(title=resolved_settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    assistant_service = AssistantService(resolved_provider, system_prompt)
    application.include_router(build_health_router(resolved_provider))
    application.include_router(build_assistant_router(assistant_service))
    application.state.model_provider = resolved_provider
    application.state.system_prompt = system_prompt
    return application


app = create_app()

# Modular Monolith Refactor Design

## Goal

Refactor the FastAPI backend into a feature-oriented modular monolith so that HTTP adapters, application use-cases, command behavior, and model integration remain independently understandable. Preserve every existing backend URL, request payload, response payload, status code, and frontend behavior.

## Non-goals

This refactor will not add a database, authentication, persistence, background jobs, arbitrary shell execution, a local LLM, new frontend features, or new public API routes.

## Module structure

The backend will use vertical feature slices with a small shared core:

```text
backend/app/
  main.py                    # composition root only
  core/
    __init__.py
    config.py                # environment-backed settings
  modules/
    __init__.py
    health/
      __init__.py
      router.py              # /health and /ready HTTP adapters
      schemas.py             # health/readiness response models
    assistant/
      __init__.py
      router.py              # /api/jarvis/* HTTP adapters
      schemas.py             # frontend request/response models
      service.py             # assistant use-cases
      commands.py            # allowlisted deterministic commands
      model.py               # provider protocol and unavailable provider
```

`main.py` is the composition root. It creates settings and service dependencies, configures middleware, and includes the health and assistant routers. It must not contain assistant behavior or endpoint-specific schemas.

The health module owns only liveness/readiness transport and schemas. The assistant module owns the complete assistant capability, command, and inference boundary. The assistant router is a thin adapter: it validates input, calls `AssistantService`, and maps `ModelNotConfiguredError` to the existing HTTP 503 error shape.

## Application service boundary

`AssistantService` is the assistant module's application boundary:

```python
class AssistantService:
    def __init__(self, model_provider: ModelProvider): ...
    def get_capabilities(self) -> CapabilitiesResponse: ...
    def execute_command(self, command: str) -> CommandResult: ...
    async def generate_inference(self, prompt: str, system: str) -> InferenceResult: ...
```

The service composes the command registry and model provider. It does not know about FastAPI request objects, HTTP status codes, or frontend query libraries.

## Preserved API contracts

The following contracts remain unchanged:

- `GET /health` returns `{"status": "ok"}` with HTTP 200.
- `GET /ready` returns `{"status": "ok", "model_configured": false}` before a model is configured.
- `GET /api/jarvis/capabilities` keeps the existing `assistant`, `localMode`, `llmConfigured`, and `capabilities` fields.
- `POST /api/jarvis/execute` keeps the existing command request and result fields, including `app` and `launchUrl`.
- `POST /api/jarvis/inference` keeps the existing prompt/system request and inference result fields.
- Unconfigured inference remains HTTP 503 with `MODEL_NOT_CONFIGURED` and its current message.

The frontend's `src/lib/api.ts` and UI do not need behavioral changes for this refactor.

## Dependency direction

Dependencies point inward toward feature behavior:

```text
main.py
  -> module routers
      -> AssistantService
          -> command registry
          -> ModelProvider protocol
              -> UnavailableModelProvider
```

Routers may depend on schemas and services from their own module. Modules may depend on `core` and standard-library abstractions. Services must not import FastAPI, `HTTPException`, or frontend code. The model provider interface must remain independent of any specific local-LLM library.

## Error handling

The assistant service raises domain/application exceptions, not HTTP exceptions. The assistant router translates only `ModelNotConfiguredError` into the preserved HTTP 503 response. Pydantic validation continues to provide standard 422 responses for malformed requests. Unknown commands continue to return a normal `CommandResult` with `handled: false`.

## Testing strategy

Existing endpoint tests remain as contract tests and must pass unchanged. Add focused unit tests for `AssistantService` and the command registry so the core behavior can be tested without an HTTP client. Add a composition test that creates the app and confirms both module routers are registered.

The refactor is complete when:

- Endpoint contract tests pass without changing their expected payloads.
- Assistant service tests cover capabilities, known commands, unknown commands, and unavailable inference.
- The application composition test confirms health and assistant routes are available.
- The existing frontend type-check and production build still pass.
- No module becomes a catch-all class or imports HTTP concerns into application services.

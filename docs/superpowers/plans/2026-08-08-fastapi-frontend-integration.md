# FastAPI + Frontend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable Conda-managed FastAPI backend that supports the existing Kaelith frontend API contract while isolating future local-LLM integration behind a provider interface.

**Architecture:** FastAPI owns typed health, readiness, capabilities, command, and inference routes. A safe command registry handles only known deterministic actions, while a `ModelProvider` protocol isolates model loading/generation from HTTP code. Vite proxies the frontend's `/api` requests to FastAPI in development; the existing React Query hooks remain unchanged.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Pydantic Settings, pytest, HTTPX, Conda, React 19, Vite 6, TypeScript.

## Global Constraints

- Do not install, download, initialize, or serve a local LLM in this iteration.
- Keep the future model behind `ModelProvider`; route code must not import a model library.
- Never pass user command input to a shell or execute arbitrary operating-system commands.
- Preserve the existing frontend response contracts in `frontend/src/lib/api.ts`.
- The backend test suite runs from `backend` in the Conda environment.
- The frontend must pass `npm run typecheck` and `npm run build`.
- The current workspace is not a Git repository; do not attempt commits unless Git is initialized before execution.

---

## File map

### Backend files

- Create `backend/environment.yml` — Conda runtime and test dependencies.
- Create `backend/app/__init__.py`, `backend/app/api/__init__.py`, `backend/app/core/__init__.py`, and `backend/app/services/__init__.py` — Python package markers.
- Create `backend/app/core/config.py` — `Settings` and environment-derived CORS configuration.
- Create `backend/app/services/model.py` — `ModelProvider`, status value object, unavailable provider, and model-not-configured exception.
- Create `backend/app/services/commands.py` — typed capability data and the explicit allowlisted command registry.
- Create `backend/app/api/health.py` — `/health` and `/ready` route handlers.
- Create `backend/app/api/jarvis.py` — `/api/jarvis/capabilities`, `/execute`, and `/inference` route handlers plus request/response schemas.
- Create `backend/app/main.py` — application factory, CORS middleware, router registration, and the default `app` object.
- Create `backend/tests/test_api.py` — real FastAPI client tests for all backend behaviors.
- Create `backend/README.md` — Conda setup and run instructions.

### Frontend files

- Modify `frontend/vite.config.ts` — proxy `/api` to the local FastAPI server during development.
- Leave `frontend/src/lib/api.ts` unchanged unless verification identifies a contract mismatch; its existing types define the backend payloads.
- Update root `README.md` — document starting both services together.

## API contracts

The implementation must use these exact payload shapes:

```python
class HealthResponse(BaseModel):
    status: Literal["ok"]

class ReadyResponse(BaseModel):
    status: Literal["ok"]
    model_configured: bool

class Capability(BaseModel):
    id: str
    label: str
    description: str
    examples: list[str]

class CapabilitiesResponse(BaseModel):
    assistant: str
    localMode: bool
    llmConfigured: bool
    capabilities: list[Capability]

class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)

class CommandResult(BaseModel):
    message: str
    handled: bool
    app: str | None = None
    launchUrl: str | None = None

class InferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    system: str = Field(default="", max_length=10_000)

class InferenceResult(BaseModel):
    model: str | None = None
    response: str
```

The inference error must be HTTP 503 with this JSON detail object until a provider is configured:

```json
{
  "detail": {
    "code": "MODEL_NOT_CONFIGURED",
    "message": "A local language model is not configured."
  }
}
```

### Task 1: Scaffold the Conda backend and implement health/readiness

**Files:**
- Create: `backend/environment.yml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/services/model.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Produces `create_app() -> FastAPI` and module-level `app` in `backend/app/main.py`.
- Produces `Settings` with `app_name`, `backend_host`, `backend_port`, and `cors_origins`.
- Produces `ModelProvider.status() -> ModelStatus` and `UnavailableModelProvider`.

- [ ] **Step 1: Write the failing tests for liveness and unloaded readiness**

Create `backend/tests/test_api.py` with:

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_reports_a_live_api():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_api_up_but_model_not_configured():
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_configured": False}
```

- [ ] **Step 2: Run the tests and verify the failure is caused by the missing app**

Run from `backend`:

```powershell
pytest tests/test_api.py -q
```

Expected: collection fails because `app.main` does not exist yet. Do not add route assertions that pass without the implementation.

- [ ] **Step 3: Add the minimal Conda environment and package scaffold**

Create `backend/environment.yml`:

```yaml
name: kaelith-backend
channels:
  - conda-forge
dependencies:
  - python=3.11
  - fastapi
  - uvicorn
  - pydantic-settings
  - pytest
  - httpx
```

Create the four package marker files as empty files. From `backend`, the environment setup command will be:

```powershell
conda env create -f environment.yml
conda activate kaelith-backend
```

- [ ] **Step 4: Implement configuration and the unavailable model provider**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Kaelith API"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:20380,http://127.0.0.1:20380"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/services/model.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModelStatus:
    configured: bool
    ready: bool


class ModelNotConfiguredError(RuntimeError):
    """Raised when inference is requested before a local model is configured."""


class ModelProvider(Protocol):
    def status(self) -> ModelStatus: ...

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]: ...


class UnavailableModelProvider:
    def status(self) -> ModelStatus:
        return ModelStatus(configured=False, ready=False)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        raise ModelNotConfiguredError
```

- [ ] **Step 5: Implement the health and readiness routes and app factory**

Create `backend/app/api/health.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.model import ModelProvider


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    model_configured: bool


def build_health_router(model_provider: ModelProvider) -> APIRouter:
    router = APIRouter(tags=["health"])

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @router.get("/ready", response_model=ReadyResponse)
    async def ready() -> ReadyResponse:
        return ReadyResponse(status="ok", model_configured=model_provider.status().configured)

    return router
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import build_health_router
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
    application.state.model_provider = resolved_provider
    return application


app = create_app()
```

- [ ] **Step 6: Run the focused tests and verify they pass**

Run:

```powershell
pytest tests/test_api.py -q
```

Expected: `2 passed`.

### Task 2: Add capabilities and safe command execution

**Files:**
- Modify: `backend/tests/test_api.py`
- Create: `backend/app/services/commands.py`
- Create: `backend/app/api/jarvis.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces `get_capabilities() -> list[Capability]` in `app/services/commands.py`.
- Produces `execute_command(command: str) -> CommandResult` in `app/services/commands.py`.
- Produces `build_jarvis_router(model_provider: ModelProvider) -> APIRouter` in `app/api/jarvis.py`.

- [ ] **Step 1: Add failing tests for capabilities and commands**

Append to `backend/tests/test_api.py`:

```python
def test_capabilities_match_the_frontend_contract():
    response = client.get("/api/jarvis/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["assistant"] == "KAELITH"
    assert body["localMode"] is True
    assert body["llmConfigured"] is False
    assert {item["id"] for item in body["capabilities"]} == {"calendar", "downloads", "time"}


def test_known_command_is_handled_without_shell_execution():
    response = client.post("/api/jarvis/execute", json={"command": "what time is it"})

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"].startswith("It is ")


def test_unknown_command_is_reported_as_unhandled():
    response = client.post("/api/jarvis/execute", json={"command": "run arbitrary shell"})

    assert response.status_code == 200
    assert response.json() == {
        "message": "I do not have a safe action for that command.",
        "handled": False,
        "app": None,
        "launchUrl": None,
    }
```

- [ ] **Step 2: Run the tests and verify the new tests fail for missing routes**

Run:

```powershell
pytest tests/test_api.py -q
```

Expected: the original two tests pass and the three new tests fail with 404 responses.

- [ ] **Step 3: Implement the command registry**

Create `backend/app/services/commands.py` with Pydantic models and an exact normalized command map:

```python
from datetime import datetime

from pydantic import BaseModel


class Capability(BaseModel):
    id: str
    label: str
    description: str
    examples: list[str]


class CommandResult(BaseModel):
    message: str
    handled: bool
    app: str | None = None
    launchUrl: str | None = None


CAPABILITIES = [
    Capability(id="calendar", label="Open calendar", description="Open the local calendar.", examples=["open calendar"]),
    Capability(id="downloads", label="Open downloads", description="Open the local downloads folder.", examples=["open downloads"]),
    Capability(id="time", label="Time check", description="Read the current local time.", examples=["what time is it"]),
]


def get_capabilities() -> list[Capability]:
    return CAPABILITIES.copy()


def execute_command(command: str) -> CommandResult:
    normalized = " ".join(command.strip().lower().split())
    if normalized == "what time is it":
        return CommandResult(message=f"It is {datetime.now().astimezone():%I:%M %p}.", handled=True)
    if normalized == "open calendar":
        return CommandResult(message="Calendar is ready to open.", handled=True, app="Calendar")
    if normalized == "open downloads":
        return CommandResult(message="Downloads is ready to open.", handled=True, app="Downloads")
    return CommandResult(message="I do not have a safe action for that command.", handled=False)
```

- [ ] **Step 4: Implement typed Jarvis routes and register them**

Create `backend/app/api/jarvis.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.commands import Capability, CommandResult, execute_command, get_capabilities
from app.services.model import ModelProvider


class CapabilitiesResponse(BaseModel):
    assistant: str
    localMode: bool
    llmConfigured: bool
    capabilities: list[Capability]


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


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

    return router
```

In `backend/app/main.py`, import `build_jarvis_router` and include it after the health router:

```python
from app.api.jarvis import build_jarvis_router

# inside create_app, after include_router(build_health_router(...))
application.include_router(build_jarvis_router(resolved_provider))
```

- [ ] **Step 5: Run the command tests and verify they pass**

Run:

```powershell
pytest tests/test_api.py -q
```

Expected: `5 passed`.

### Task 3: Add the unavailable-model inference endpoint

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/api/jarvis.py`

**Interfaces:**
- Consumes the `ModelProvider` and `ModelNotConfiguredError` from Task 1.
- Produces `POST /api/jarvis/inference` with the existing frontend request and response shape.

- [ ] **Step 1: Add the failing inference test**

Append to `backend/tests/test_api.py`:

```python
def test_inference_reports_model_not_configured():
    response = client.post(
        "/api/jarvis/inference",
        json={"prompt": "Say hello", "system": "Be brief."},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "MODEL_NOT_CONFIGURED",
            "message": "A local language model is not configured.",
        }
    }
```

- [ ] **Step 2: Run the test and verify it fails because the route is missing**

Run:

```powershell
pytest tests/test_api.py::test_inference_reports_model_not_configured -q
```

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Implement the inference request, response, and error mapping**

Add to `backend/app/api/jarvis.py`:

```python
from fastapi import HTTPException

from app.services.model import ModelNotConfiguredError


class InferenceRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    system: str = Field(default="", max_length=10_000)


class InferenceResult(BaseModel):
    model: str | None = None
    response: str


# inside build_jarvis_router
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
```

- [ ] **Step 4: Run the complete backend suite**

Run from `backend`:

```powershell
pytest -q
```

Expected: `6 passed`.

### Task 4: Wire Vite to FastAPI and document the two-process workflow

**Files:**
- Modify: `frontend/vite.config.ts`
- Create: `backend/README.md`
- Modify: `README.md`

**Interfaces:**
- Development requests from the frontend to `/api/*` are proxied to `http://127.0.0.1:8000`.
- `VITE_API_URL` continues to override the relative `/api` base in `frontend/src/lib/api.ts`.

- [ ] **Step 1: Add the Vite proxy configuration**

In `frontend/vite.config.ts`, add this `server.proxy` entry while preserving the existing server settings:

```typescript
server: {
  port,
  strictPort: true,
  host: '0.0.0.0',
  allowedHosts: true,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    },
  },
  fs: {
    strict: true,
  },
},
```

- [ ] **Step 2: Document backend setup and startup**

Create `backend/README.md` with these commands:

````markdown
# Kaelith backend

## Setup

```powershell
conda env create -f environment.yml
conda activate kaelith-backend
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. The local development frontend reaches it through Vite's `/api` proxy.

## Test

```powershell
pytest -q
```

The inference endpoint intentionally reports `MODEL_NOT_CONFIGURED` until a local LLM provider is installed and wired into the `ModelProvider` interface.
````

- [ ] **Step 3: Document starting both services in the root README**

Replace the empty root `README.md` with:

````markdown
# Kaelith

Kaelith is a local-first desktop assistant interface.

## Development

Start the backend in one shell:

```powershell
conda activate kaelith-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another shell:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `/api` during development and Vite proxies those requests to FastAPI. Set `VITE_API_URL` when calling a separately hosted backend.
````

- [ ] **Step 4: Run frontend checks**

From `frontend`:

```powershell
npm run typecheck
npm run build
```

Expected: both commands exit with code 0.

### Task 5: Perform full integration verification

**Files:**
- Modify only files needed to correct failures discovered during verification.

- [ ] **Step 1: Verify backend tests from the Conda environment**

From `backend` with `kaelith-backend` active:

```powershell
pytest -q
```

Expected: `6 passed` with no warnings or errors.

- [ ] **Step 2: Start FastAPI and verify live HTTP responses**

In a backend shell:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second shell, verify:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
Invoke-RestMethod http://127.0.0.1:8000/api/jarvis/capabilities
```

Expected: health is `ok`, readiness reports `model_configured: false`, capabilities reports `localMode: true` and `llmConfigured: false`.

- [ ] **Step 3: Re-run frontend typecheck and build after backend integration**

From `frontend`:

```powershell
npm run typecheck
npm run build
```

Expected: both commands exit with code 0.

- [ ] **Step 4: Review the final diff and scope**

Confirm the diff contains only the backend scaffold, backend tests/configuration, Vite proxy, and setup documentation. Confirm there are no LLM packages, model downloads, arbitrary shell execution, database code, or authentication code.

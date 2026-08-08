# Modular Monolith Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the FastAPI backend into health and assistant feature modules while preserving every existing HTTP and frontend contract.

**Architecture:** `main.py` remains a composition root only. Feature slices under `app/modules/` own schemas, routers, application services, and domain-facing adapters; the assistant router delegates to `AssistantService`, which composes command behavior and the model provider.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, HTTPX, existing Conda environment.

## Global Constraints

- Preserve every existing backend URL, request payload, response payload, status code, and frontend behavior.
- Services must not import FastAPI, `HTTPException`, or frontend code.
- Do not add a database, authentication, persistence, background jobs, arbitrary shell execution, local LLM, or public API routes.
- Existing endpoint contract tests must remain unchanged and pass.
- The frontend's `src/lib/api.ts` and UI must not receive behavioral changes.

---

### Task 1: Add failing module-boundary tests

**Files:**
- Create: `backend/tests/test_modules.py`

**Interfaces:**
- Defines the expected `AssistantService`, `ModelStatus`, `ModelProvider`, `UnavailableModelProvider`, and module router composition interfaces before implementation.

- [ ] **Step 1: Write failing unit and composition tests**

Create `backend/tests/test_modules.py`:

```python
import pytest

from app.main import app
from app.modules.assistant.model import ModelStatus, UnavailableModelProvider
from app.modules.assistant.service import AssistantService


class ConfiguredProvider:
    def status(self) -> ModelStatus:
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str) -> tuple[str | None, str]:
        return "test-model", f"response to: {prompt}"


def test_assistant_service_exposes_capabilities_and_commands():
    service = AssistantService(ConfiguredProvider())

    capabilities = service.get_capabilities()
    command = service.execute_command("what time is it")

    assert capabilities.assistant == "KAELITH"
    assert capabilities.llmConfigured is True
    assert command.handled is True


@pytest.mark.anyio
async def test_assistant_service_returns_provider_inference():
    result = await AssistantService(ConfiguredProvider()).generate_inference("hello", "be brief")

    assert result.model == "test-model"
    assert result.response == "response to: hello"


@pytest.mark.anyio
async def test_unavailable_provider_is_exposed_without_http_concerns():
    with pytest.raises(Exception) as raised:
        await AssistantService(UnavailableModelProvider()).generate_inference("hello", "")

    assert raised.value.__class__.__name__ == "ModelNotConfiguredError"


def test_app_composes_health_and_assistant_modules():
    paths = {route.path for route in app.routes}

    assert {"/health", "/ready", "/api/jarvis/capabilities", "/api/jarvis/execute", "/api/jarvis/inference"} <= paths
```

- [ ] **Step 2: Run the new tests and verify they fail for missing modules**

Run from `backend`:

```powershell
& 'C:\Users\Adriaan M. Dimate\anaconda3\Scripts\conda.exe' run --no-capture-output -n kaelith-backend python -m pytest tests/test_modules.py -q
```

Expected: collection fails because `app.modules` does not exist yet.

### Task 2: Create feature modules and move behavior behind AssistantService

**Files:**
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/health/__init__.py`
- Create: `backend/app/modules/health/schemas.py`
- Create: `backend/app/modules/health/router.py`
- Create: `backend/app/modules/assistant/__init__.py`
- Create: `backend/app/modules/assistant/schemas.py`
- Create: `backend/app/modules/assistant/commands.py`
- Create: `backend/app/modules/assistant/model.py`
- Create: `backend/app/modules/assistant/service.py`
- Create: `backend/app/modules/assistant/router.py`

**Interfaces:**
- `AssistantService(model_provider)` exposes `get_capabilities()`, `execute_command(command)`, and async `generate_inference(prompt, system)`.
- `build_health_router(model_provider)` returns the health `APIRouter`.
- `build_assistant_router(assistant_service)` returns the `/api/jarvis` `APIRouter`.

- [ ] **Step 1: Implement assistant schemas and provider boundary**

Move the existing Pydantic payload models into `backend/app/modules/assistant/schemas.py` unchanged, and move the existing provider code into `backend/app/modules/assistant/model.py`. Preserve field names including `localMode`, `llmConfigured`, `launchUrl`, and `model`.

- [ ] **Step 2: Implement the assistant command module**

Move the existing `Capability`, `CommandResult`, `CAPABILITIES`, `get_capabilities()`, and `execute_command()` into `backend/app/modules/assistant/commands.py` without changing command normalization, messages, or allowlisted behavior.

- [ ] **Step 3: Implement AssistantService**

Create `backend/app/modules/assistant/service.py`:

```python
from app.modules.assistant.commands import execute_command, get_capabilities
from app.modules.assistant.model import ModelProvider
from app.modules.assistant.schemas import (
    CapabilitiesResponse,
    CommandResult,
    InferenceResult,
)


class AssistantService:
    def __init__(self, model_provider: ModelProvider):
        self._model_provider = model_provider

    def get_capabilities(self) -> CapabilitiesResponse:
        return CapabilitiesResponse(
            assistant="KAELITH",
            localMode=True,
            llmConfigured=self._model_provider.status().configured,
            capabilities=get_capabilities(),
        )

    def execute_command(self, command: str) -> CommandResult:
        return execute_command(command)

    async def generate_inference(self, prompt: str, system: str) -> InferenceResult:
        model, response = await self._model_provider.generate(prompt, system)
        return InferenceResult(model=model, response=response)
```

- [ ] **Step 4: Implement thin module routers**

`health/router.py` should contain the existing health/readiness response models imported from `health/schemas.py` and only call `model_provider.status()`.

`assistant/router.py` should define request validation with the schemas, call `AssistantService`, and map only `ModelNotConfiguredError` to the existing HTTP 503 detail:

```python
except ModelNotConfiguredError as error:
    raise HTTPException(
        status_code=503,
        detail={
            "code": "MODEL_NOT_CONFIGURED",
            "message": "A local language model is not configured.",
        },
    ) from error
```

No route should contain command matching, capability data, or model-provider calls.

- [ ] **Step 5: Run module tests and verify they pass**

Run:

```powershell
& 'C:\Users\Adriaan M. Dimate\anaconda3\Scripts\conda.exe' run --no-capture-output -n kaelith-backend python -m pytest tests/test_modules.py -q
```

Expected: `4 passed`.

### Task 3: Switch composition root and remove stale duplicate boundaries

**Files:**
- Modify: `backend/app/main.py`
- Delete: `backend/app/api/health.py`
- Delete: `backend/app/api/jarvis.py`
- Delete: `backend/app/services/commands.py`
- Delete: `backend/app/services/model.py`
- Delete: `backend/app/api/__init__.py`
- Delete: `backend/app/services/__init__.py`

**Interfaces:**
- `create_app(settings=None, model_provider=None) -> FastAPI` remains unchanged.
- `app` remains the module-level FastAPI instance imported by existing tests and Uvicorn.

- [ ] **Step 1: Update main.py as composition root**

Use only these application dependencies in `backend/app/main.py`:

```python
from app.modules.assistant.model import ModelProvider, UnavailableModelProvider
from app.modules.assistant.router import build_assistant_router
from app.modules.assistant.service import AssistantService
from app.modules.health.router import build_health_router
```

Construct one provider and one assistant service, register both module routers, keep the existing CORS middleware, and keep `application.state.model_provider` for compatibility.

- [ ] **Step 2: Run all backend contract tests**

Run:

```powershell
& 'C:\Users\Adriaan M. Dimate\anaconda3\Scripts\conda.exe' run --no-capture-output -n kaelith-backend python -m pytest -q
```

Expected: existing API tests plus module tests pass with unchanged payload assertions.

- [ ] **Step 3: Confirm no stale imports remain**

Run:

```powershell
rg -n "app\.api|app\.services" backend/app backend/tests
```

Expected: no matches; all runtime imports should point to `app.modules` or `app.core`.

### Task 4: Final integration verification

**Files:**
- Modify none unless a failing verification requires a contract-preserving correction.

- [ ] **Step 1: Run backend tests**

Expected: all tests pass; the existing FastAPI/httpx deprecation warning may remain from the environment.

- [ ] **Step 2: Run frontend checks**

From `frontend`:

```powershell
npm.cmd run typecheck
npm.cmd run build
```

Expected: both exit 0; no frontend source changes are needed.

- [ ] **Step 3: Smoke-test the live API**

Verify `/health`, `/ready`, `/api/jarvis/capabilities`, and `/api/jarvis/inference` retain their current status and payloads.

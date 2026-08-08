# System Prompt Loading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the backend load `ai/system-prompt.md` at application startup and use its contents for every local LLM inference request.

**Architecture:** Add a small UTF-8 prompt loader at the application boundary. `Settings` supplies a repository-root-based default path, `create_app` loads the file once, and `AssistantService` owns the loaded prompt while the model providers continue receiving plain strings. Keep the request `system` field accepted for HTTP compatibility, but do not use it.

**Tech Stack:** Python 3.11, FastAPI, Pydantic Settings, pytest, existing `ModelProvider` protocol.

## Global Constraints

- The canonical prompt is `ai/system-prompt.md`.
- The prompt is loaded once during `create_app`.
- Missing, unreadable, or invalid UTF-8 prompt files fail application creation clearly.
- The request-provided `system` value must not replace the loaded prompt.
- Editing the prompt requires a backend restart.
- Existing health, readiness, capabilities, command, and model error behavior must remain intact.
- Each task ends with a focused passing test and one meaningful commit.

---

### Task 1: Add the configured prompt path

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_config.py`

**Interfaces:**
- Produces `DEFAULT_SYSTEM_PROMPT_PATH: Path` and `Settings.system_prompt_path: str`.

- [ ] **Step 1: Write the failing test**

Add:

```python
from pathlib import Path

from app.core.config import DEFAULT_SYSTEM_PROMPT_PATH, Settings


def test_settings_default_system_prompt_path_points_to_repository_prompt():
    settings = Settings()

    assert Path(settings.system_prompt_path) == DEFAULT_SYSTEM_PROMPT_PATH
    assert DEFAULT_SYSTEM_PROMPT_PATH.as_posix().endswith("ai/system-prompt.md")
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_config.py::test_settings_default_system_prompt_path_points_to_repository_prompt -q` from the repository root.

Expected: FAIL because `system_prompt_path` and `DEFAULT_SYSTEM_PROMPT_PATH` do not exist.

- [ ] **Step 3: Implement the setting**

In `backend/app/core/config.py`, add:

```python
DEFAULT_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[3] / "ai" / "system-prompt.md"
```

and add this field to `Settings`:

```python
system_prompt_path: str = str(DEFAULT_SYSTEM_PROMPT_PATH)
```

- [ ] **Step 4: Run the focused test**

Run `pytest backend/tests/test_config.py::test_settings_default_system_prompt_path_points_to_repository_prompt -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/core/config.py backend/tests/test_config.py
git commit -m "feat: configure system prompt path"
```

### Task 2: Define prompt-loading errors

**Files:**
- Create: `backend/app/core/system_prompt.py`
- Create: `backend/tests/test_system_prompt.py`

**Interfaces:**
- Produces `SystemPromptConfigurationError(RuntimeError)` for prompt configuration failures.

- [ ] **Step 1: Write the failing test**

Add:

```python
from app.core.system_prompt import SystemPromptConfigurationError


def test_system_prompt_configuration_error_is_a_runtime_error():
    assert issubclass(SystemPromptConfigurationError, RuntimeError)
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_system_prompt.py::test_system_prompt_configuration_error_is_a_runtime_error -q`.

Expected: FAIL because the module and exception do not exist.

- [ ] **Step 3: Implement the error type**

Create `backend/app/core/system_prompt.py` with:

```python
class SystemPromptConfigurationError(RuntimeError):
    """Raised when the configured system prompt cannot be loaded."""
```

- [ ] **Step 4: Run the focused test**

Run `pytest backend/tests/test_system_prompt.py::test_system_prompt_configuration_error_is_a_runtime_error -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/core/system_prompt.py backend/tests/test_system_prompt.py
git commit -m "feat: define system prompt configuration error"
```

### Task 3: Implement strict UTF-8 prompt loading

**Files:**
- Modify: `backend/app/core/system_prompt.py`
- Modify: `backend/tests/test_system_prompt.py`

**Interfaces:**
- Produces `load_system_prompt(path: Path) -> str`.

- [ ] **Step 1: Write the failing tests**

Add:

```python
from pathlib import Path

import pytest

from app.core.system_prompt import SystemPromptConfigurationError, load_system_prompt


def test_load_system_prompt_reads_exact_utf8_contents(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("You are Jazrielle.\nRéponds brièvement.", encoding="utf-8")

    assert load_system_prompt(prompt_path) == "You are Jazrielle.\nRéponds brièvement."


def test_load_system_prompt_rejects_missing_file(tmp_path: Path):
    with pytest.raises(SystemPromptConfigurationError, match="does not exist"):
        load_system_prompt(tmp_path / "missing.md")


def test_load_system_prompt_rejects_invalid_utf8(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_bytes(b"valid text\xff")

    with pytest.raises(SystemPromptConfigurationError, match="UTF-8"):
        load_system_prompt(prompt_path)
```

- [ ] **Step 2: Run the focused tests**

Run `pytest backend/tests/test_system_prompt.py -q`.

Expected: FAIL because `load_system_prompt` does not exist.

- [ ] **Step 3: Implement the loader**

Add:

```python
from pathlib import Path


def load_system_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise SystemPromptConfigurationError(
            f"System prompt file cannot be read: {path}"
        ) from error
```

- [ ] **Step 4: Run the focused tests**

Run `pytest backend/tests/test_system_prompt.py -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/core/system_prompt.py backend/tests/test_system_prompt.py
git commit -m "feat: load system prompt as strict utf8"
```

### Task 4: Load the prompt during app composition

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- `create_app(settings=Settings(system_prompt_path=...), model_provider=...)` loads the configured file before returning the app.

- [ ] **Step 1: Write the failing test**

Add a fake provider that records the system value and test custom settings:

```python
from pathlib import Path

from app.core.config import Settings
from app.main import create_app
from app.modules.assistant.model import ModelStatus


class RecordingProvider:
    def __init__(self):
        self.system = None

    def status(self):
        return ModelStatus(configured=True, ready=True)

    async def generate(self, prompt: str, system: str):
        self.system = system
        return "test-model", "ok"


def test_create_app_reads_configured_system_prompt(tmp_path: Path):
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("custom prompt", encoding="utf-8")
    provider = RecordingProvider()

    application = create_app(
        settings=Settings(system_prompt_path=str(prompt_path)),
        model_provider=provider,
    )

    assert application.state.system_prompt == "custom prompt"
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_api.py::test_create_app_reads_configured_system_prompt -q`.

Expected: FAIL because app composition does not load or store the prompt.

- [ ] **Step 3: Implement app-boundary loading**

In `backend/app/main.py`, import `load_system_prompt`, load `Path(resolved_settings.system_prompt_path)` after resolving settings, and assign the resulting string to `application.state.system_prompt`.

- [ ] **Step 4: Run the focused test**

Run `pytest backend/tests/test_api.py::test_create_app_reads_configured_system_prompt -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat: load system prompt during app startup"
```

### Task 5: Inject the loaded prompt into the assistant service

**Files:**
- Modify: `backend/app/modules/assistant/service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_modules.py`

**Interfaces:**
- `AssistantService(model_provider: ModelProvider, system_prompt: str)` stores the canonical prompt.
- `AssistantService.generate_inference(prompt: str)` calls the provider with the stored prompt.

- [ ] **Step 1: Write the failing test**

Replace the service inference test with:

```python
@pytest.mark.anyio
async def test_assistant_service_uses_injected_system_prompt():
    provider = RecordingProvider()

    result = await AssistantService(provider, "canonical prompt").generate_inference("hello")

    assert result.model == "test-model"
    assert result.response == "response to: hello"
    assert provider.system == "canonical prompt"
```

Update the fake provider to record `system` in `generate`.

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_modules.py::test_assistant_service_uses_injected_system_prompt -q`.

Expected: FAIL because the service constructor and method still require the request system argument.

- [ ] **Step 3: Implement service injection**

Change the service constructor to accept `system_prompt`, store it as `_system_prompt`, change `generate_inference` to accept only `prompt`, and call:

```python
model, response = await self._model_provider.generate(prompt, self._system_prompt)
```

In `main.py`, construct the service with `AssistantService(resolved_provider, system_prompt)`.

- [ ] **Step 4: Run the focused test**

Run `pytest backend/tests/test_modules.py::test_assistant_service_uses_injected_system_prompt -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/main.py backend/app/modules/assistant/service.py backend/tests/test_modules.py
git commit -m "feat: inject canonical prompt into assistant service"
```

### Task 6: Keep the HTTP field compatible but ignore it

**Files:**
- Modify: `backend/app/modules/assistant/router.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- `POST /api/jarvis/inference` still accepts `{"prompt": str, "system": str}`.
- The route calls `assistant_service.generate_inference(payload.prompt)`.

- [ ] **Step 1: Write the failing test**

Add:

```python
def test_inference_ignores_request_system_prompt(tmp_path):
    provider = RecordingProvider()
    prompt_path = tmp_path / "system-prompt.md"
    prompt_path.write_text("file prompt", encoding="utf-8")
    client = TestClient(create_app(
        settings=Settings(system_prompt_path=str(prompt_path)),
        model_provider=provider,
    ))

    response = client.post(
        "/api/jarvis/inference",
        json={"prompt": "hello", "system": "caller override"},
    )

    assert response.status_code == 200
    assert provider.system == "file prompt"
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_api.py::test_inference_ignores_request_system_prompt -q`.

Expected: FAIL because the route still forwards `payload.system`.

- [ ] **Step 3: Update the route**

Change the route call to:

```python
return await assistant_service.generate_inference(payload.prompt)
```

- [ ] **Step 4: Run the focused test**

Run `pytest backend/tests/test_api.py::test_inference_ignores_request_system_prompt -q`.

Expected: PASS.

- [ ] **Step 5: Commit**

```text
git add backend/app/modules/assistant/router.py backend/tests/test_api.py
git commit -m "fix: ignore caller system prompt"
```

### Task 7: Verify the provider receives a system message

**Files:**
- Modify: `backend/tests/test_model_provider.py`

**Interfaces:**
- Preserve `ModelProvider.generate(prompt: str, system: str)` and verify its chat-message contract.

- [ ] **Step 1: Add the missing assertion**

In the existing fake llama test, assert:

```python
assert kwargs["messages"][0] == {"role": "system", "content": "be brief"}
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_model_provider.py::test_llama_provider_loads_lazily_and_returns_chat_content -q`.

Expected: PASS, confirming the provider already honors the service contract.

- [ ] **Step 3: Commit**

```text
git add backend/tests/test_model_provider.py
git commit -m "test: verify model provider system message"
```

### Task 8: Test startup failure for missing prompt files

**Files:**
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- `create_app(settings=Settings(system_prompt_path=missing_path), ...)` raises `SystemPromptConfigurationError`.

- [ ] **Step 1: Write the test**

Add:

```python
import pytest

from app.core.system_prompt import SystemPromptConfigurationError


def test_create_app_fails_when_system_prompt_is_missing(tmp_path):
    with pytest.raises(SystemPromptConfigurationError, match="does not exist"):
        create_app(settings=Settings(system_prompt_path=str(tmp_path / "missing.md")))
```

- [ ] **Step 2: Run the focused test**

Run `pytest backend/tests/test_api.py::test_create_app_fails_when_system_prompt_is_missing -q`.

Expected: PASS using the loader’s startup error.

- [ ] **Step 3: Commit**

```text
git add backend/tests/test_api.py
git commit -m "test: cover missing system prompt startup failure"
```

### Task 9: Update the root development README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Document the exact backend startup command and canonical prompt location.

- [ ] **Step 1: Add prompt-loading documentation**

Under the development instructions, state that the backend reads `ai/system-prompt.md` at startup, that the file must exist and be UTF-8, and that backend restart is required after edits.

- [ ] **Step 2: Review the rendered Markdown text**

Run `Get-Content -Raw README.md` and verify the command remains:

```powershell
cd backend
conda activate jazrielle-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- [ ] **Step 3: Commit**

```text
git add README.md
git commit -m "docs: explain backend system prompt startup"
```

### Task 10: Update the backend README

**Files:**
- Modify: `backend/README.md`

**Interfaces:**
- Document setup, run, test, and prompt-file requirements for backend contributors.

- [ ] **Step 1: Add the prompt section**

Explain that `ai/system-prompt.md` is loaded during startup, is authoritative over the request `system` field, must be valid UTF-8, and requires a backend restart after changes.

- [ ] **Step 2: Verify backend instructions**

Run `Get-Content -Raw backend/README.md` and confirm the existing conda, uvicorn, and pytest commands remain intact.

- [ ] **Step 3: Commit**

```text
git add backend/README.md
git commit -m "docs: document backend prompt configuration"
```

### Task 11: Run the complete backend regression suite

**Files:**
- Modify: `backend/tests/test_modules.py` if any remaining service call sites need the new signature.
- Modify: `backend/tests/test_api.py` if any remaining inference fixtures need the new app settings.

**Interfaces:**
- All existing tests use the canonical prompt service contract.

- [ ] **Step 1: Search for stale call sites**

Run `rg -n "generate_inference\(|AssistantService\(" backend` and update every call to pass the service prompt in the constructor and only the user prompt to `generate_inference`.

- [ ] **Step 2: Run all backend tests**

Run `pytest backend/tests -q`.

Expected: all tests pass.

- [ ] **Step 3: Commit any compatibility test updates**

```text
git add backend/tests
git commit -m "test: align backend suite with canonical prompt"
```

### Task 12: Verify the real prompt file and final documentation

**Files:**
- Verify: `ai/system-prompt.md`
- Verify: `README.md`
- Verify: `backend/README.md`

**Interfaces:**
- The default application can start with the repository’s actual prompt file.

- [ ] **Step 1: Run the default-path smoke check**

Run from `backend`:

```powershell
python -c "from app.main import app; print(app.state.system_prompt[:20])"
```

Expected: output begins with the first characters of `ai/system-prompt.md`.

- [ ] **Step 2: Run the complete suite again**

Run `pytest backend/tests -q`.

Expected: all tests pass.

- [ ] **Step 3: Commit final verification metadata if needed**

If the verification requires a test-only adjustment, commit it with:

```text
git add backend/tests
git commit -m "test: verify default system prompt integration"
```


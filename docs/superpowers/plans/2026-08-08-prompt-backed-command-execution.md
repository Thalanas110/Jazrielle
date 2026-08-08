# Prompt-Backed Command Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route every command through `ai/system-prompt.md`, validate the model's JSON intent, and execute the complete declared action set through safe, configured handlers.

**Architecture:** `AssistantService` will interpret commands with the existing `ModelProvider` and canonical prompt, parse a typed `AssistantIntent`, and dispatch it to an explicit action registry. Windows, network, persistence, Git, media, and project operations will be isolated behind injected adapters. Application and project targets will be loaded from `ai/assistant-actions.json`.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, pytest, `llama-cpp-python`, `psutil`, Windows standard-library APIs, React/TypeScript, Vite.

## Global Constraints

- Never pass model output to a shell or execute with `shell=True`.
- Never accept executable paths, project directories, process names, or arbitrary command arrays from model arguments.
- Resolve application and project targets only from `ai/assistant-actions.json`.
- Preserve the frontend `CommandResult` fields: `message`, `handled`, `app`, and `launchUrl`.
- Keep the canonical prompt loaded from `ai/system-prompt.md`; the request body cannot override it.
- Write a failing test before each production change and commit each task independently.
- Produce at least 14 implementation commits, excluding the already committed design spec.

## File Map

| File | Responsibility |
| --- | --- |
| `backend/app/modules/assistant/intent.py` | Typed model intent and JSON parser. |
| `backend/app/modules/assistant/action_config.py` | Safe application/project configuration models and loader. |
| `backend/app/modules/assistant/action_registry.py` | Typed action dispatch and result normalization. |
| `backend/app/modules/assistant/adapters/` | OS, network, persistence, Git, media, and project adapter protocols/implementations. |
| `backend/app/modules/assistant/commands.py` | Capability metadata and compatibility aliases backed by the registry. |
| `backend/app/modules/assistant/service.py` | Prompt-backed interpretation and dispatch. |
| `backend/app/modules/assistant/router.py` | Async API route and structured command errors. |
| `backend/app/core/config.py` | Default action-config path and environment settings. |
| `backend/app/main.py` | Application composition and adapter wiring. |
| `backend/tests/` | Unit, integration, and API regression tests. |
| `ai/assistant-actions.json` | Explicit target and local integration configuration. |
| `ai/system-prompt.md` | Canonical intent-selection instructions. |
| `frontend/src/lib/api.ts` | Structured command error handling. |
| `frontend/src/App.tsx` | Command status presentation and full capability compatibility. |
| `backend/environment.yml` | Runtime dependencies for Windows metrics/media adapters. |
| `backend/README.md` | Configuration and action setup documentation. |

---

### Task 1: Add typed model intents and a strict JSON parser

**Files:**
- Create: `backend/app/modules/assistant/intent.py`
- Create: `backend/tests/test_intent.py`

**Interfaces:**
- Produces `AssistantIntent`, `IntentParseError`, and `parse_intent(response: str) -> AssistantIntent`.
- `AssistantIntent.action` is restricted to the 20 action names in `ai/system-prompt.md`.
- `AssistantIntent.arguments` is a dictionary and `message` is a non-empty string.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from app.modules.assistant.intent import IntentParseError, parse_intent


def test_parse_intent_accepts_canonical_json():
    intent = parse_intent('{"action":"get_time","arguments":{},"message":"Checking the time."}')

    assert intent.action == "get_time"
    assert intent.arguments == {}
    assert intent.message == "Checking the time."


def test_parse_intent_accepts_a_json_code_fence():
    intent = parse_intent('```json\n{"action":"conversation","arguments":{},"message":"Hello."}\n```')

    assert intent.action == "conversation"


@pytest.mark.parametrize("response", ["not json", '{"action":"not_allowed","arguments":{},"message":"x"}'])
def test_parse_intent_rejects_invalid_model_output(response: str):
    with pytest.raises(IntentParseError):
        parse_intent(response)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run from `backend` after activating `jazrielle-backend`:

```powershell
pytest -q tests/test_intent.py
```

Expected: collection fails because `app.modules.assistant.intent` does not exist.

- [ ] **Step 3: Implement the minimal parser**

Create `intent.py` with a `Literal` action union, Pydantic model, code-fence stripping, `json.loads`, and conversion of JSON/Pydantic errors into `IntentParseError`.

- [ ] **Step 4: Run the focused test to verify it passes**

```powershell
pytest -q tests/test_intent.py
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/intent.py backend/tests/test_intent.py
git commit -m "feat: validate model command intents"
```

### Task 2: Add explicit application and project configuration

**Files:**
- Create: `backend/app/modules/assistant/action_config.py`
- Create: `backend/tests/test_action_config.py`
- Create: `ai/assistant-actions.json`
- Modify: `backend/app/core/config.py`

**Interfaces:**
- Produces `ApplicationTarget`, `ProjectTarget`, `AssistantActionConfig`, and `load_action_config(path: Path) -> AssistantActionConfig`.
- Application targets expose `label`, `launch_target`, and optional `process_name`.
- Project targets expose `working_directory`, fixed `start_command: list[str]`, and optional `process_name`.

- [ ] **Step 1: Write the failing tests**

```python
import json

import pytest

from app.modules.assistant.action_config import ConfigError, load_action_config


def test_load_action_config_resolves_declared_targets(tmp_path):
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(json.dumps({
        "applications": {"calendar": {"label": "Calendar", "launchTarget": "Calendar"}},
        "projects": {"demo": {"workingDirectory": str(tmp_path), "startCommand": ["python", "-m", "demo"]}},
    }), encoding="utf-8")

    config = load_action_config(config_path)

    assert config.applications["calendar"].launch_target == "Calendar"
    assert config.projects["demo"].working_directory == tmp_path.resolve()


def test_load_action_config_rejects_project_outside_configured_root(tmp_path):
    config_path = tmp_path / "assistant-actions.json"
    config_path.write_text(json.dumps({
        "projects": {"bad": {"workingDirectory": str(tmp_path / "missing"), "startCommand": ["python"]}},
    }), encoding="utf-8")

    with pytest.raises(ConfigError):
        load_action_config(config_path)
```

- [ ] **Step 2: Run the test and verify the expected failure**

```powershell
pytest -q tests/test_action_config.py
```

Expected: import failure for `action_config`.

- [ ] **Step 3: Implement config models and the default JSON file**

Use Pydantic aliases for `launchTarget`, `processName`, `workingDirectory`, and `startCommand`. Resolve paths relative to the JSON file, reject non-existent project directories, reject empty commands, and add the existing Calendar and Downloads targets to the default file without adding arbitrary executables.

- [ ] **Step 4: Run the test and full config checks**

```powershell
pytest -q tests/test_action_config.py tests/test_config.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/action_config.py backend/tests/test_action_config.py backend/app/core/config.py ai/assistant-actions.json
git commit -m "feat: add explicit assistant action targets"
```

### Task 3: Introduce the action registry and safe result handling

**Files:**
- Create: `backend/app/modules/assistant/action_registry.py`
- Create: `backend/tests/test_action_registry.py`
- Create: `backend/tests/support.py`
- Modify: `backend/app/modules/assistant/commands.py`

**Interfaces:**
- Produces `ActionHandler`, `ActionRegistry`, and `build_action_registry(config, adapters) -> ActionRegistry`.
- `ActionRegistry.execute(intent: AssistantIntent) -> CommandResult` rejects unknown or unregistered actions before invoking a handler.
- `get_capabilities()` returns metadata derived from registered actions.
- `backend/tests/support.py` provides `intent(action, arguments=None, message="Checking.")` for later focused tests.

- [ ] **Step 1: Write the failing tests**

```python
import pytest

from app.modules.assistant.action_registry import ActionRegistry, UnknownActionError
from app.modules.assistant.intent import parse_intent


def test_registry_executes_a_registered_handler():
    registry = ActionRegistry({"conversation": lambda intent: {"message": intent.message, "handled": True}})

    result = registry.execute(parse_intent('{"action":"conversation","arguments":{},"message":"Hello."}'))

    assert result.handled is True
    assert result.message == "Hello."


def test_registry_rejects_unregistered_actions():
    registry = ActionRegistry({})

    with pytest.raises(UnknownActionError):
        registry.execute(parse_intent('{"action":"get_time","arguments":{},"message":"Checking."}'))
```

- [ ] **Step 2: Verify the tests fail**

```powershell
pytest -q tests/test_action_registry.py
```

Expected: import failure for `action_registry`.

- [ ] **Step 3: Implement registry normalization and the test helper**

Normalize handler returns into `CommandResult`, reject missing handlers, preserve optional `app` and `launchUrl`, and expose capability metadata without making the registry execute arbitrary callables supplied by model data. Add this test helper:

```python
def intent(action: str, arguments: dict | None = None, message: str = "Checking.") -> AssistantIntent:
    return AssistantIntent(action=action, arguments=arguments or {}, message=message)
```

- [ ] **Step 4: Verify tests pass and old exact aliases still pass**

```powershell
pytest -q tests/test_action_registry.py tests/test_api.py -k "known_command or capabilities"
```

Expected: selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/action_registry.py backend/tests/test_action_registry.py backend/app/modules/assistant/commands.py
git commit -m "feat: add safe assistant action registry"
```

### Task 4: Route command execution through the canonical prompt

**Files:**
- Modify: `backend/app/modules/assistant/service.py`
- Modify: `backend/tests/test_modules.py`

**Interfaces:**
- Changes `AssistantService.execute_command(command: str)` to `async def execute_command(command: str) -> CommandResult`.
- The method calls `ModelProvider.generate(command, self._system_prompt)`, parses the response with `parse_intent`, and dispatches to `ActionRegistry`.

- [ ] **Step 1: Write the failing service test**

```python
@pytest.mark.anyio
async def test_execute_command_uses_canonical_prompt_and_model_intent():
    provider = ConfiguredProvider(response='{"action":"conversation","arguments":{},"message":"Understood."}')
    registry = ActionRegistry({"conversation": lambda intent: {"message": intent.message, "handled": True}})
    service = AssistantService(provider, "canonical prompt", action_registry=registry)

    result = await service.execute_command("please acknowledge this")

    assert result.message == "Understood."
    assert provider.system == "canonical prompt"
    assert provider.prompt == "please acknowledge this"
```

- [ ] **Step 2: Run the focused test and confirm it fails**

```powershell
pytest -q tests/test_modules.py::test_execute_command_uses_canonical_prompt_and_model_intent
```

Expected: `ConfiguredProvider` has no JSON response field and `execute_command` is not awaitable.

- [ ] **Step 3: Implement async service composition**

Inject an `ActionRegistry` into `AssistantService`, preserve the existing constructor's required provider and prompt arguments, and use the injected registry for command dispatch.

- [ ] **Step 4: Verify service tests**

```powershell
pytest -q tests/test_modules.py
```

Expected: all service tests pass after updating the test provider to record `prompt`, `system`, and its JSON response.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/service.py backend/tests/test_modules.py
git commit -m "feat: interpret commands with canonical prompt"
```

### Task 5: Make the API route async and map command errors

**Files:**
- Modify: `backend/app/modules/assistant/router.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/modules/assistant/intent.py`

**Interfaces:**
- The route awaits `assistant_service.execute_command`.
- `IntentParseError`, `ModelNotConfiguredError`, and `ModelRuntimeUnavailableError` map to structured HTTP errors.

- [ ] **Step 1: Add failing API tests**

```python
def test_natural_language_command_is_interpreted_by_model():
    application = create_app(model_provider=ConfiguredJsonProvider(
        '{"action":"conversation","arguments":{},"message":"I understand."}'
    ))

    response = TestClient(application).post("/api/jarvis/execute", json={"command": "please acknowledge"})

    assert response.status_code == 200
    assert response.json()["message"] == "I understand."
```

- [ ] **Step 2: Run the API test and confirm the old sync path fails**

```powershell
pytest -q tests/test_api.py::test_natural_language_command_is_interpreted_by_model
```

Expected: the endpoint returns an error because the test provider and route are not yet wired for async intent execution.

- [ ] **Step 3: Implement route error mapping**

Await the service call. Return 422 for malformed model intent, 503 for unavailable model/runtime, and keep successful `CommandResult` responses at 200.

- [ ] **Step 4: Run the API suite**

```powershell
pytest -q tests/test_api.py
```

Expected: all API tests pass after replacing the old unknown-command assertion with malformed/unsupported-action coverage.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/router.py backend/app/modules/assistant/intent.py backend/tests/test_api.py
git commit -m "feat: expose prompt-backed command errors"
```

### Task 6: Add time, date, and system-status adapters

**Files:**
- Create: `backend/app/modules/assistant/adapters/system.py`
- Create: `backend/tests/test_system_actions.py`
- Modify: `backend/app/modules/assistant/action_registry.py`

**Interfaces:**
- `SystemAdapter.get_time()`, `get_date()`, and `get_system_status()` return serializable values.
- Handlers for `get_time`, `get_date`, and `get_system_status` use the adapter and return handled `CommandResult` values.

- [ ] **Step 1: Write tests using a fake adapter**

```python
def test_get_time_uses_system_adapter():
    registry = build_action_registry(config=test_config(), adapters=FakeAdapters(system=FakeSystemAdapter(time="11:30 PM")))

    result = registry.execute(intent("get_time"))

    assert result.handled is True
    assert result.message == "It is 11:30 PM."
```

- [ ] **Step 2: Run and observe failure**

```powershell
pytest -q tests/test_system_actions.py
```

Expected: missing adapter and handler failure.

- [ ] **Step 3: Implement the adapter protocol, Windows implementation, and handlers**

Use `datetime.now().astimezone()` for local time/date and `platform`, `socket`, and `os` for non-invasive system status. Keep the fake adapter interface identical to production.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_system_actions.py tests/test_action_registry.py
```

Expected: selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/system.py backend/app/modules/assistant/action_registry.py backend/tests/test_system_actions.py
git commit -m "feat: add time date and system status actions"
```

### Task 7: Add CPU, memory, and top-process metrics

**Files:**
- Modify: `backend/environment.yml`
- Create: `backend/app/modules/assistant/adapters/metrics.py`
- Create: `backend/tests/test_metrics_actions.py`
- Modify: `backend/app/modules/assistant/action_registry.py`

**Interfaces:**
- `MetricsAdapter.cpu_usage()`, `memory_usage()`, and `top_processes(limit: int)` return typed dictionaries/lists.
- Handlers validate `limit` and return concise JSON-safe messages.

- [ ] **Step 1: Write fake-adapter tests**

```python
def test_top_processes_limits_and_formats_results():
    registry = build_action_registry(config=test_config(), adapters=FakeAdapters(metrics=FakeMetricsAdapter(top=[{"name": "python", "memory_mb": 120}])))

    result = registry.execute(intent("get_top_processes", {"limit": 1}))

    assert result.handled is True
    assert "python" in result.message
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_metrics_actions.py
```

Expected: missing metrics adapter/handlers.

- [ ] **Step 3: Implement psutil adapter and validation**

Add `psutil` to `environment.yml`. Use `psutil.cpu_percent`, `psutil.virtual_memory`, and `psutil.process_iter` with exception handling for vanished or inaccessible processes; never expose command lines.

- [ ] **Step 4: Verify green**

```powershell
pytest -q tests/test_metrics_actions.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/environment.yml backend/app/modules/assistant/adapters/metrics.py backend/app/modules/assistant/action_registry.py backend/tests/test_metrics_actions.py
git commit -m "feat: add resource and process metrics"
```

### Task 8: Add allowlisted application and project controls

**Files:**
- Create: `backend/app/modules/assistant/adapters/processes.py`
- Create: `backend/tests/test_process_actions.py`
- Modify: `backend/app/modules/assistant/action_registry.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- `ProcessAdapter.start(command, cwd)`, `stop(process_name)`, and `open_target(target)` are injected into handlers.
- `open_application`, `close_application`, `start_project`, and `stop_project` resolve identifiers only through `AssistantActionConfig`.

- [ ] **Step 1: Write allowlist tests**

```python
def test_open_application_returns_only_configured_target():
    registry = build_action_registry(config=config_with_calendar(), adapters=FakeAdapters(processes=FakeProcessAdapter()))

    result = registry.execute(intent("open_application", {"application": "calendar"}))

    assert result.handled is True
    assert result.app == "Calendar"


def test_unknown_application_is_not_executed():
    processes = FakeProcessAdapter()
    registry = build_action_registry(config=config_with_calendar(), adapters=FakeAdapters(processes=processes))

    result = registry.execute(intent("open_application", {"application": "powershell"}))

    assert result.handled is False
    assert processes.calls == []
```

- [ ] **Step 2: Run red**

```powershell
pytest -q tests/test_process_actions.py
```

Expected: missing process adapter and handlers.

- [ ] **Step 3: Implement safe process adapter and handlers**

Use `subprocess.Popen` and `subprocess.run` with argument lists and `shell=False`; validate config entries before use; use configured process names for stop operations. Do not accept an executable, cwd, or process name from intent arguments.

- [ ] **Step 4: Compose the registry in `create_app` and verify**

```powershell
pytest -q tests/test_process_actions.py tests/test_api.py
```

Expected: selected tests pass with no process launched by tests.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/processes.py backend/app/modules/assistant/action_registry.py backend/app/main.py backend/tests/test_process_actions.py
git commit -m "feat: add configured application and project controls"
```

### Task 9: Add local reminder persistence

**Files:**
- Create: `backend/app/modules/assistant/adapters/reminders.py`
- Create: `backend/tests/test_reminder_actions.py`
- Modify: `ai/assistant-actions.json`
- Modify: `backend/app/modules/assistant/action_registry.py`

**Interfaces:**
- `ReminderStore.create(message, due_at) -> Reminder` and `list() -> list[Reminder]`.
- `create_reminder` validates a non-empty message and ISO/local time; `list_reminders` returns stored reminders.

- [ ] **Step 1: Write persistence tests**

```python
def test_create_and_list_reminder_round_trip(tmp_path):
    store = JsonReminderStore(tmp_path / "reminders.json")

    created = store.create("Submit report", "2030-01-01T20:00:00+08:00")

    assert store.list()[0].message == created.message == "Submit report"
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_reminder_actions.py
```

Expected: missing reminder store.

- [ ] **Step 3: Implement atomic JSON persistence and handlers**

Create the parent directory, write UTF-8 JSON through a temporary sibling file followed by `Path.replace`, and keep the schema limited to `id`, `message`, `dueAt`, and `createdAt`.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_reminder_actions.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/reminders.py backend/app/modules/assistant/action_registry.py backend/tests/test_reminder_actions.py ai/assistant-actions.json
git commit -m "feat: add local reminder actions"
```

### Task 10: Add weather and update providers

**Files:**
- Create: `backend/app/modules/assistant/adapters/network.py`
- Create: `backend/tests/test_network_actions.py`
- Modify: `backend/app/modules/assistant/action_registry.py`

**Interfaces:**
- `WeatherProvider.get_weather(location) -> WeatherReport`.
- `UpdateProvider.get_updates() -> UpdateReport`.
- Both are injected; tests use fakes and never call the network or package manager.

- [ ] **Step 1: Write fake-provider tests**

```python
def test_weather_action_uses_requested_or_configured_location():
    registry = build_action_registry(config=test_config(), adapters=FakeAdapters(weather=FakeWeatherProvider("Manila: 30 C, clear")))

    result = registry.execute(intent("get_weather", {"location": "Manila"}))

    assert result.handled is True
    assert result.message == "Manila: 30 C, clear"
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_network_actions.py
```

Expected: missing provider and handlers.

- [ ] **Step 3: Implement bounded providers**

Use `urllib.request` against the fixed HTTPS weather endpoint with a timeout and URL-encoded location. Implement updates through a fixed provider interface; the Windows implementation may call a fixed `winget upgrade --include-unknown` argument list with `shell=False`, never model-provided arguments.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_network_actions.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/network.py backend/app/modules/assistant/action_registry.py backend/tests/test_network_actions.py
git commit -m "feat: add weather and update actions"
```

### Task 11: Add media playback and volume controls

**Files:**
- Create: `backend/app/modules/assistant/adapters/media.py`
- Create: `backend/tests/test_media_actions.py`
- Modify: `backend/environment.yml`
- Modify: `backend/app/modules/assistant/action_registry.py`

**Interfaces:**
- `MediaAdapter.play()`, `pause()`, and `set_volume(percent: int)` are injected into handlers.
- Volume is constrained to 0–100 before reaching the adapter.

- [ ] **Step 1: Write fake-adapter tests**

```python
def test_set_volume_rejects_values_outside_zero_to_hundred():
    adapter = FakeMediaAdapter()
    registry = build_action_registry(config=test_config(), adapters=FakeAdapters(media=adapter))

    result = registry.execute(intent("set_volume", {"level": 120}))

    assert result.handled is False
    assert adapter.calls == []
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_media_actions.py
```

Expected: missing media adapter and handlers.

- [ ] **Step 3: Implement Windows media adapter**

Use the Windows media play/pause virtual key through a small adapter and `pycaw` for endpoint volume. Add the dependency in `environment.yml`; keep all platform imports inside the adapter module and return a clear unavailable result when not on Windows.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_media_actions.py
```

Expected: selected tests pass without changing the host volume.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/media.py backend/app/modules/assistant/action_registry.py backend/environment.yml backend/tests/test_media_actions.py
git commit -m "feat: add media and volume actions"
```

### Task 12: Add URL validation and Git status

**Files:**
- Create: `backend/app/modules/assistant/adapters/git.py`
- Create: `backend/tests/test_url_git_actions.py`
- Modify: `backend/app/modules/assistant/action_registry.py`
- Modify: `ai/assistant-actions.json`

**Interfaces:**
- `GitAdapter.status(repository: Path) -> str` runs only fixed Git status arguments.
- `open_url` returns `launchUrl` only for `http` and `https` URLs with a host.
- `git_status` reads only the configured repository path.

- [ ] **Step 1: Write failing validation and adapter tests**

```python
def test_open_url_rejects_non_web_schemes():
    result = build_action_registry(config=test_config(), adapters=FakeAdapters()).execute(intent("open_url", {"url": "file:///secret.txt"}))

    assert result.handled is False


def test_git_status_uses_configured_repository_and_fixed_args():
    git = FakeGitAdapter("## main")
    result = build_action_registry(config=test_config(), adapters=FakeAdapters(git=git)).execute(intent("git_status", {}))

    assert result.handled is True
    assert result.message == "## main"
    assert git.repository == configured_repository()
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_url_git_actions.py
```

Expected: missing handlers/adapters.

- [ ] **Step 3: Implement URL and Git boundaries**

Parse URLs with `urllib.parse.urlparse`, require an HTTP(S) scheme and non-empty netloc, and use `subprocess.run(["git", "-C", str(repo), "status", "--short", "--branch"], shell=False, check=False, capture_output=True, text=True)` for the configured repository only.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_url_git_actions.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/adapters/git.py backend/app/modules/assistant/action_registry.py backend/tests/test_url_git_actions.py ai/assistant-actions.json
git commit -m "feat: add safe URL and Git actions"
```

### Task 13: Complete capability metadata and prompt contract

**Files:**
- Modify: `backend/app/modules/assistant/commands.py`
- Modify: `backend/tests/test_api.py`
- Modify: `ai/system-prompt.md`

**Interfaces:**
- `GET /api/jarvis/capabilities` reports every registered action and its examples.
- The prompt explicitly states that action arguments must match the action schemas and that unavailable targets must not be invented.

- [ ] **Step 1: Write the failing capability contract test**

```python
def test_capabilities_expose_the_complete_prompt_action_set():
    body = client.get("/api/jarvis/capabilities").json()
    ids = {item["id"] for item in body["capabilities"]}

    assert {"open_application", "get_memory_usage", "create_reminder", "git_status", "conversation"} <= ids
```

- [ ] **Step 2: Verify red**

```powershell
pytest -q tests/test_api.py::test_capabilities_expose_the_complete_prompt_action_set
```

Expected: the current three-item capability list does not contain the complete action set.

- [ ] **Step 3: Derive capabilities from the registered handlers and strengthen the prompt**

Keep the prompt's JSON output schema, add concise argument requirements for target-sensitive actions, and ensure capability examples use valid configured identifiers.

- [ ] **Step 4: Verify**

```powershell
pytest -q tests/test_api.py::test_capabilities_expose_the_complete_prompt_action_set tests/test_api.py::test_capabilities_match_the_frontend_contract
```

Expected: both tests pass.

- [ ] **Step 5: Commit**

```powershell
git add backend/app/modules/assistant/commands.py backend/tests/test_api.py ai/system-prompt.md
git commit -m "feat: expose complete prompt action contract"
```

### Task 14: Improve frontend command errors and document setup

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `backend/README.md`
- Create: `frontend/src/lib/api.test.ts` if the existing test setup supports it; otherwise verify through the TypeScript build.

**Interfaces:**
- API mutations preserve structured backend error messages where available.
- The UI presents model/configuration/action errors distinctly from network failures.
- Backend documentation explains `ai/assistant-actions.json`, the full action set, and required Windows dependencies.

- [ ] **Step 1: Add the failing frontend contract test or build assertion**

If a frontend test runner is available, assert that a response body such as `{ "detail": { "message": "That project is not configured." } }` becomes an error with that message. If no runner exists, add the typed helper and use `npm run build` as the red check after intentionally referencing the missing helper.

- [ ] **Step 2: Verify red**

```powershell
cd frontend
npm run build
```

Expected: the new contract test/helper is not yet implemented.

- [ ] **Step 3: Implement structured error extraction and UI copy**

Parse JSON error bodies in `useExecuteJarvisCommand`, expose the message through the mutation error, and render the backend message in the command error notice with a retry action. Document setup and safe target configuration in `backend/README.md`.

- [ ] **Step 4: Verify green**

```powershell
npm run build
```

Expected: frontend build exits 0.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/lib/api.ts frontend/src/App.tsx backend/README.md frontend/src/lib/api.test.ts
git commit -m "feat: show structured command errors"
```

### Task 15: Add end-to-end composition coverage and finish verification

**Files:**
- Create: `backend/tests/test_command_integration.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/app/main.py` only if composition coverage finds a missing adapter registration.

**Interfaces:**
- A configured fake model response can traverse the real FastAPI route, intent parser, registry, and a fake adapter without external side effects.
- The complete backend and frontend verification commands are recorded in the test output.

- [ ] **Step 1: Write the failing end-to-end test**

```python
def test_command_route_uses_prompt_intent_and_registered_handler():
    provider = ConfiguredJsonProvider(
        '{"action":"get_time","arguments":{},"message":"Checking the time."}'
    )
    application = create_app(model_provider=provider, adapters=fake_adapters())

    response = TestClient(application).post("/api/jarvis/execute", json={"command": "tell me the time"})

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert response.json()["message"] == "It is 11:30 PM."
    assert provider.system == DEFAULT_SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the integration test and inspect the failure**

```powershell
pytest -q tests/test_command_integration.py
```

Expected: any remaining composition mismatch is reported before final verification.

- [ ] **Step 3: Implement only the missing composition wiring**

Register the action config, adapters, and action registry in `create_app`; do not change handler behavior in this final task.

- [ ] **Step 4: Run complete verification**

```powershell
cd backend
pytest -q
cd ..\frontend
npm run build
```

Expected: backend exits with zero failures and frontend build exits 0.

- [ ] **Step 5: Commit**

```powershell
git add backend/tests/test_command_integration.py backend/tests/test_api.py backend/app/main.py
git commit -m "test: verify end-to-end prompt command execution"
```

This plan produces 15 implementation commits, exceeding the required minimum of 13.

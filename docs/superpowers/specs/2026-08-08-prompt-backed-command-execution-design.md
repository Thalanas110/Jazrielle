# Prompt-Backed Command Execution Design

## Goal

Make the command surface use the canonical `ai/system-prompt.md` for every natural-language command while preserving a strict execution boundary. The local model chooses an intent; application code validates and executes only explicitly registered actions.

## Current problem

`POST /api/jarvis/execute` currently calls an exact-match function that recognizes only `what time is it`, `open calendar`, and `open downloads`. The canonical system prompt is loaded into `AssistantService` for inference, but command execution bypasses it. As a result, natural-language requests fall through to `I do not have a safe action for that command.` even when the prompt describes the requested capability.

## Architecture

The command path will be:

```text
user command
    -> AssistantService + canonical system prompt
    -> ModelProvider JSON intent
    -> Pydantic intent validation
    -> explicit action registry
    -> bounded action handler
    -> existing CommandResult response
```

`AssistantService` owns prompt-backed interpretation. The model response will use the existing prompt schema:

```json
{
  "action": "ACTION_NAME",
  "arguments": {},
  "message": "SHORT_RESPONSE"
}
```

The model cannot execute a command directly. A validated action is passed to a registry whose handlers are the only code allowed to cause side effects or return launch targets.

The route may become asynchronous because model-backed interpretation calls the asynchronous `ModelProvider.generate` method. The HTTP response contract remains `CommandResult` with `message`, `handled`, `app`, and `launchUrl` fields so the current frontend stays compatible.

## Action coverage

The registry will cover every action currently declared in `ai/system-prompt.md`:

- `open_application` and `close_application`
- `get_system_status`, `get_cpu_usage`, `get_memory_usage`, and `get_top_processes`
- `get_time`, `get_date`, and `get_weather`
- `play_media`, `pause_media`, and `set_volume`
- `create_reminder` and `list_reminders`
- `get_updates`
- `start_project` and `stop_project`
- `git_status`
- `open_url`
- `conversation`

Each action will have a typed argument model and an explicit handler. If the host environment lacks a required integration or a target has not been configured, the handler will return a specific unavailable/configuration message rather than silently treating the command as an unknown command.

## Configuration

`ai/assistant-actions.json` will be the explicit target registry for target-specific operations.

Applications will define a stable identifier, display name, launch target, and optional process name. Projects will define a stable identifier, working directory, fixed start argument list, and optional process identifier or stop behavior. Handlers will resolve only entries from this file.

The configuration boundary will enforce:

- no model-provided executable paths or arbitrary command strings;
- no shell parsing or `shell=True` subprocesses;
- project working directories constrained to configured paths;
- application close operations constrained to configured process names;
- URL launches restricted to supported web schemes and validated URLs;
- reminder storage constrained to the configured local data path.

The file will contain only safe defaults needed by the existing application. Users can add their own application and project entries explicitly.

## Data flow and failure behavior

1. The command route sends the raw user command to the local provider with the canonical prompt loaded at application startup.
2. The provider response is parsed as JSON and validated against the intent schema.
3. The registry rejects unknown actions, invalid arguments, and unconfigured targets before any handler runs.
4. A successful handler returns a normal `CommandResult`.

Failures will be distinct:

- unavailable model: a model-configuration/runtime error;
- malformed model output: an understandable request error;
- valid but unconfigured target: a configuration error;
- unsupported or unsafe action: a rejected-action result;
- handler/runtime failure: a bounded action failure without exposing raw traceback details.

The current exact commands may remain as deterministic aliases for degraded operation when the model is unavailable, but normal command interpretation will use the canonical prompt rather than phrase matching.

## Implementation boundaries

Windows-specific integrations will live behind small adapter interfaces. This keeps action selection and validation platform-independent and makes tests able to exercise handlers without opening applications, changing volume, starting processes, or making network calls.

Likely adapters include:

- desktop/application launching and process control;
- system metrics and process inspection;
- media and volume control;
- weather and update providers;
- reminder persistence;
- project process management;
- Git status collection.

Network and operating-system work will use fixed, validated inputs and will not accept executable code from the model.

## Testing strategy

Tests will be written before implementation and will cover:

- the canonical prompt being passed to the provider for command execution;
- valid intent parsing, including the complete action set;
- malformed JSON, unknown actions, and invalid arguments;
- allowlist enforcement for applications and projects;
- URL, path, process, and subprocess safety rules;
- each action handler through injected adapters;
- configured and unavailable model behavior at service and API levels;
- preservation of the existing frontend response shape;
- deterministic aliases for the existing three commands, if retained.

The final verification will run the complete backend test suite and the frontend build/type checks.

# System Prompt Loading Design

## Goal

Make `ai/system-prompt.md` the backend-owned system prompt for every local LLM inference request. The backend must read the file itself so callers cannot accidentally omit or replace the assistant's core instructions.

## Approved approach

The FastAPI application loads the Markdown file once while the application is being created. The loaded UTF-8 text is injected into `AssistantService`, which passes it to the model provider for every inference. The inference request's existing `system` field remains accepted for temporary API compatibility, but its value is ignored by the backend.

The default path is derived from the repository location rather than the process working directory:

```text
<repository root>/ai/system-prompt.md
```

The path is exposed through backend settings so deployments and tests can provide a different prompt file when needed.

## Components and data flow

1. `app.core.config.Settings` defines the default system-prompt path.
2. App composition reads the configured file as UTF-8 during `create_app`.
3. `AssistantService` stores the loaded prompt as an immutable service dependency.
4. The inference route passes only the user prompt to the service.
5. The service calls `ModelProvider.generate(user_prompt, loaded_system_prompt)`.

This keeps file I/O at the application boundary and keeps model providers unaware of filesystem paths. The model provider continues to receive plain prompt text through its existing interface.

## Error handling

If the configured prompt file does not exist, cannot be read, or cannot be decoded as UTF-8, application creation fails immediately with a clear configuration error. This prevents the backend from starting in a state where inference would silently run without the required instructions.

## Compatibility

The request schema may continue to expose `system` during this change so existing clients do not break at the HTTP validation layer. It is not used to construct the model messages. The README will document the canonical file and explain that the backend must be restarted after editing it because the prompt is loaded at startup.

## Verification

Add tests that:

- load a temporary Markdown prompt through app settings;
- assert the exact file contents reach a fake model provider;
- assert a request-provided `system` value does not replace the loaded prompt;
- assert missing prompt files fail app creation clearly;
- preserve existing health, capabilities, command, and model error behavior.


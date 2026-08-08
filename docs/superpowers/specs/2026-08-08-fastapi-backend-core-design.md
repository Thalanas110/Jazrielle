# Core FastAPI Backend Design

## Goal

Create a small, runnable Python FastAPI backend in the existing `backend` directory and wire it to the existing frontend. It should provide service health reporting, support the frontend's current assistant contract, and provide a stable seam for adding a lightweight local model later, without installing, loading, or serving a model yet.

## Scope

The first backend iteration includes:

- A FastAPI application with `GET /health` and `GET /ready`.
- FastAPI routes for the frontend's existing capabilities, command, and inference requests.
- Environment-backed application settings with safe local defaults.
- A model-provider abstraction representing the future local LLM dependency.
- An explicit safe command registry; arbitrary shell execution is excluded.
- Tests for health, readiness, capabilities, command, and unavailable-model behavior.
- A Vite development proxy so the frontend's default `/api` base reaches FastAPI.
- A Conda environment definition and local run/test documentation.

It explicitly excludes databases, authentication, model files, model downloads, background workers, arbitrary shell execution, and deployment configuration.

## Architecture

The backend will use a small layered layout:

```text
backend/
  app/
    __init__.py
    main.py
    api/
      __init__.py
      health.py
    core/
      __init__.py
      config.py
    services/
      __init__.py
      model.py
      commands.py
  tests/
    test_api.py
  environment.yml
  README.md
```

`app/main.py` creates the FastAPI application and registers routes. `app/api/health.py` owns health/readiness behavior. `app/core/config.py` owns environment-backed settings. `app/services/model.py` defines the model-provider contract and its initial unavailable implementation. `app/services/commands.py` owns the small allowlisted command registry used by the current frontend.

Routes depend on service contracts rather than on concrete model or operating-system libraries. When a local LLM is introduced later, its provider can replace the unavailable implementation without moving model-specific logic into the HTTP layer. The command service may return live information such as the current local time and known launch targets, but it will never pass user input to a shell.

The frontend keeps its existing React Query hooks and response types. In development, Vite proxies `/api` to the FastAPI server. `VITE_API_URL` remains available when the frontend must call a separately hosted backend.

## API behavior

`GET /health` is a liveness check and returns HTTP 200 with a small JSON payload indicating that the API process is running.

`GET /ready` asks the model provider whether the application is ready to serve model work. Before a model is installed, it returns HTTP 200 with a payload that clearly identifies the API as running and the model as not configured. It does not download or initialize anything.

`GET /api/jarvis/capabilities` returns the assistant identity, local-mode state, LLM configuration state, and the deterministic capabilities rendered by the frontend.

`POST /api/jarvis/execute` accepts `{ "command": "..." }` and returns the frontend's `CommandResult` shape. Known allowlisted commands are handled locally. Unknown commands return HTTP 200 with `handled: false` and an explanatory message.

`POST /api/jarvis/inference` accepts the existing `{ "prompt": "...", "system": "..." }` payload. Until a model provider is configured, it returns HTTP 503 with a structured `MODEL_NOT_CONFIGURED` error. A future provider will preserve the existing `InferenceResult` success shape.

The initial API will rely on FastAPI's standard validation and error handling. No custom error envelope is needed for these two parameterless endpoints.

## Configuration and environment

The Conda environment will contain the minimal runtime and test dependencies: Python, FastAPI, Uvicorn, Pydantic Settings, and pytest with HTTP client support.

Configuration will use environment variables where useful, with local development defaults. CORS will allow the local Vite development origin and any explicitly configured frontend origins. No secrets or model-specific settings are required in this iteration.

## Testing

Tests will exercise the real FastAPI application through its test client and verify:

1. `/health` returns HTTP 200 and the expected liveness status.
2. `/ready` returns HTTP 200 and reports that the API is running while the model is not configured.
3. Capabilities match the frontend's expected response shape.
4. Known commands are handled without arbitrary execution and unknown commands are reported as unhandled.
5. Inference returns the expected structured unavailable-model error until a provider exists.

The backend test suite must run from the `backend` directory in the Conda environment. The frontend must pass TypeScript checking and a production Vite build after the proxy configuration is added.

## Success criteria

- A developer can create the Conda environment, activate it, start the API, and call the health/readiness and frontend endpoints.
- The existing frontend can load capabilities and call command/inference routes through its default `/api` base in development.
- Backend tests pass without a model dependency, and the frontend type-check/build pass.
- The future local LLM integration point is explicit and isolated from route code.
- User command input is never executed as arbitrary shell code.
- No model is downloaded or initialized as a side effect of starting the backend.

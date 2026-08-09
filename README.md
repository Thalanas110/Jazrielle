# Jazrielle

Jazrielle is a local-first personal desktop assistant for Windows. The current development build is a React/Vite interface backed by a FastAPI service and an optional local Qwen model. It can interpret natural-language requests, validate them against a fixed action registry, and return safe results without accepting arbitrary shell commands.

## Current status

The browser build can:

- interpret commands through the canonical prompt in `ai/system-prompt.md`;
- report time, date, system and resource status;
- manage reminders and retrieve weather or update information;
- control supported media and volume actions;
- open validated web URLs;
- resolve explicitly allowlisted applications such as Calendar, Downloads, and Spotify;
- expose a separate open-ended local inference panel.

The browser can display an application result, but browser security prevents it from launching Windows applications directly. Native launching is reserved for a future desktop wrapper, such as Tauri, through the `window.jazrielleDesktop` bridge.

## Architecture

```text
React/Vite frontend (:20380)
        |  /api proxy
        v
FastAPI backend (:8000)
        |
        +-- ai/system-prompt.md       canonical model instructions
        +-- ai/assistant-actions.json  application/project allowlist
        +-- local ModelProvider        optional Qwen GGUF runtime
        +-- validated ActionRegistry   deterministic handlers
```

For a command, the backend sends the user text with the canonical system prompt to the local model. The model selects an intent; Pydantic validation checks the action and arguments; then the action registry handles only registered actions. The model never supplies executable commands or arbitrary paths to the operating system.

## Repository layout

```text
ai/
  system-prompt.md        authoritative prompt for inference and commands
  assistant-actions.json  explicit application/project configuration
backend/
  app/                    FastAPI application and assistant modules
  tests/                  backend test suite
  environment.yml         Conda environment definition
frontend/
  src/                    React interface and API hooks
start-jazrielle.*         launch scripts for PowerShell, CMD, and Bash
```

## Prerequisites

- Windows for the desktop adapters and intended runtime.
- Conda or Miniconda.
- Python 3.11 through the provided Conda environment.
- Node.js and npm for the frontend.
- A local model file at `ai/qwen3-0.6b-q4_k_m.gguf` if model-backed commands and inference are required. GGUF files are intentionally ignored by Git.

## Installation

Create the backend environment:

```powershell
conda env create -f backend/environment.yml
conda activate jazrielle-backend
```

Install frontend dependencies:

```powershell
cd frontend
npm install
```

Place the supported local GGUF model at `ai/qwen3-0.6b-q4_k_m.gguf`. The backend can start without it, but model-backed endpoints will report that the model is not configured.

## Running in development

Start both services from the repository root with the launcher for your shell:

```powershell
.\start-jazrielle.ps1
```

```cmd
start-jazrielle.cmd
```

```bash
bash ./start-jazrielle.sh
```

Or run each service manually. In one shell:

```powershell
cd backend
conda activate jazrielle-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another shell:

```powershell
cd frontend
npm run dev
```

Open the frontend at `http://localhost:20380`. The backend is available at `http://127.0.0.1:8000`. Vite proxies `/api` requests to the backend; set `VITE_API_URL` when using a separately hosted backend. The frontend port can be changed with `PORT`.

## Prompt and action configuration

`ai/system-prompt.md` is loaded at backend startup and is authoritative for both command interpretation and the open-ended inference endpoint. The request-level `system` value is retained for API compatibility but does not override the file. Restart the backend after editing the prompt.

`ai/assistant-actions.json` is the explicit allowlist for applications and projects. An application entry contains a stable identifier, display label, launch target, and optional process name:

```json
{
  "applications": {
    "spotify": {
      "label": "Spotify",
      "launchTarget": "Spotify",
      "processName": "Spotify.exe"
    }
  }
}
```

The current application targets are Calendar, Downloads, and Spotify. Project targets are discovered at backend startup by recursively finding Git repositories under `settings.projectRoot`, which is the approved `Desktop\development` tree. Hidden directories, `.git`, `.worktrees`, and `node_modules` are skipped. Unique repository folder names become identifiers; duplicate names use their normalized relative paths. Add a repository under the root and restart the backend to make it available.

Every discovered project uses the fixed VS Code command `cmd.exe /d /s /c "code.cmd ."` and `Code.exe` as its process name. Projects outside the root are rejected, and the model cannot supply a raw path, executable, or command.

Restart the backend after editing `assistant-actions.json`, because configuration is loaded during application startup.

## API endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Liveness check |
| `GET /ready` | Backend and model readiness |
| `GET /api/jarvis/capabilities` | Registered assistant capabilities |
| `POST /api/jarvis/execute` | Interpret and execute a safe command |
| `POST /api/jarvis/inference` | Run open-ended local inference |

Example command request:

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/jarvis/execute `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"command":"what time is it"}'
```

The command response contains a user-facing `message`, a `handled` flag, and optional `app` or `launchUrl` metadata. Google-search requests use the registered `search_google` action, fetch result titles and snippets in the backend, and return them in `message` without opening a browser or setting `launchUrl`. The frontend passes launch metadata to a desktop bridge only for actions that actually need it.

Online lookup example:

```json
{
  "action": "search_google",
  "arguments": {
    "query": "color coded rainfall warning for Cebu province right now"
  },
  "message": "Searching Google."
}
```

## Browser and native-desktop boundary

The development UI runs as a normal web page. It cannot call `CreateProcess`, launch `code.exe`, open Spotify directly, or perform other unrestricted desktop actions. The local backend can execute the fixed, allowlisted project command and perform server-side Google lookups; application launch metadata still requires a native wrapper. When one is added, it should expose a narrow bridge such as:

```ts
window.jazrielleDesktop.openTarget({ app, url })
```

The wrapper, not the model, must map application targets to native operations. Tauri is the planned option for that boundary. Until then, configured project commands and Google searches can be handled by the local backend, while browser-only application launching remains unavailable.

## Testing and verification

Run the backend tests:

```powershell
cd backend
conda activate jazrielle-backend
pytest -q
```

Check the frontend types and production build:

```powershell
cd frontend
npm run typecheck
npm run build
```

## Troubleshooting

### The command endpoint returns `422`

The backend returns `422` for an empty or structurally invalid model intent, or for an action that is not registered. Search requests must use the registered `search_google` action; they should not be emitted as `open_url` or an invented action. Plain-text conversational model responses are normalized into safe conversation results. Check that the backend is running the current code and that the local model is responding with the action schema in `ai/system-prompt.md`.

### An application says it is not configured

The application identifier must exist in `ai/assistant-actions.json`, and the backend must be restarted after changing that file. The model should use the configured identifier, such as `spotify`.

### The UI says an application is opening but nothing launches

This is expected in the browser-only development build. A native desktop wrapper must implement `window.jazrielleDesktop.openTarget` before Windows applications can be launched.

### The model is unavailable

Confirm that `ai/qwen3-0.6b-q4_k_m.gguf` exists and that the `jazrielle-backend` Conda environment was created successfully. The `llama-cpp-python` dependency is installed from the CPU wheel source declared in `backend/environment.yml`.

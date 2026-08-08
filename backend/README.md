# Jazrielle backend

## Setup

```powershell
conda env create -f environment.yml
conda activate jazrielle-backend
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`. The local development frontend reaches it through Vite's `/api` proxy.

## System prompt

At startup, the backend loads the authoritative system prompt from `ai/system-prompt.md`. The file must exist and contain valid UTF-8 text. Its contents are used for every inference and command-interpretation request; the request `system` field is retained only for HTTP compatibility and does not override the file. Restart the backend after editing the prompt.

## Action configuration

`ai/assistant-actions.json` is the explicit allowlist for application and project targets. Add an application under `applications` with a label and launch target, or add a project under `projects` with an existing working directory, fixed `startCommand` array, and optional process name. Model output can select only these configured identifiers; it cannot provide executable paths, process names, or command arrays.

The command endpoint supports the actions declared in `ai/system-prompt.md`: applications, system status and metrics, time/date/weather, media and volume, reminders, updates, project controls, Git status, web URLs, and conversation. The backend validates every model response before dispatching it to a registered handler.

The metrics and media adapters require the `psutil` and `pycaw` dependencies declared in `environment.yml`. Recreate or update the Conda environment after changing dependencies.

## Test

```powershell
pytest -q
```

The inference endpoint intentionally reports `MODEL_NOT_CONFIGURED` until a local LLM provider is installed and wired into the `ModelProvider` interface.

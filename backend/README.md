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

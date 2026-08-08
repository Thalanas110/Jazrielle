# Jazrielle

Jazrielle is a local-first desktop assistant interface.

## Development

Start the backend in one shell:

```powershell
cd backend
conda activate jazrielle-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend reads the canonical system prompt from `ai/system-prompt.md` when it starts. Keep that file present and UTF-8 encoded; restart the backend after editing it so the new prompt is loaded.

To start both services at once, use the launcher for your shell from the repository root:

```powershell
.\start-jazrielle.ps1
```

```cmd
start-jazrielle.cmd
```

```bash
bash ./start-jazrielle.sh
```

Start the frontend in another shell:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `/api` during development and Vite proxies those requests to FastAPI. Set `VITE_API_URL` when calling a separately hosted backend.

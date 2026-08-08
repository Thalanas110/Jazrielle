# Kaelith

Kaelith is a local-first desktop assistant interface.

## Development

Start the backend in one shell:

```powershell
cd backend
conda activate kaelith-backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in another shell:

```powershell
cd frontend
npm install
npm run dev
```

The frontend uses `/api` during development and Vite proxies those requests to FastAPI. Set `VITE_API_URL` when calling a separately hosted backend.

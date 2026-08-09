# Standalone Tauri Installer Design

## Goal

Ship Jazrielle as one Windows installer that contains the Tauri floating UI, a packaged FastAPI backend, the local Qwen model, and the backend's prompt/action assets. The installed app must start and stop its backend automatically without requiring Python, Conda, Node.js, or a second installer on the user's machine.

## Scope

This feature covers the Windows desktop runtime and distribution path:

- freeze the FastAPI backend into a Windows executable with PyInstaller;
- bundle that executable as a Tauri sidecar;
- bundle the 484 MB `ai/qwen3-0.6b-q4_k_m.gguf` model plus the prompt and action configuration into the same Tauri package;
- start the sidecar silently when Tauri starts and terminate it when Tauri exits;
- point the production frontend at the local backend while preserving the Vite `/api` proxy in browser development;
- enable NSIS and MSI output from the existing Tauri build command;
- document development, sidecar preparation, installer generation, and runtime behavior.

## Non-goals

- macOS or Linux packaging;
- code signing, notarization, automatic updates, or Microsoft Store submission;
- changing the assistant action registry or model behavior;
- adding a second installer for the backend;
- embedding the backend as a Rust rewrite.

## Architecture

The backend will be built from `backend/sidecar.py` with PyInstaller's one-file Windows mode. The generated executable will be placed at `src-tauri/binaries/jazrielle-backend-x86_64-pc-windows-msvc.exe`; this is a generated local artifact and will remain ignored by Git. Tauri's `bundle.externalBin` configuration will include it in the single installer.

At Tauri startup, the Rust app initializes `tauri-plugin-shell`, starts the `jazrielle-backend` sidecar, and supplies the absolute paths for the bundled `ai` assets through the child process environment. The backend remains bound to `127.0.0.1:8000`. Tauri keeps the sidecar child handle and kills it during application exit. If the bundled sidecar cannot start, the app reports a clear startup failure rather than silently pretending the assistant is online.

The frontend API base becomes environment-aware: `VITE_API_URL` remains highest priority, browser builds retain `/api`, and Tauri builds use `http://127.0.0.1:8000/api`. The backend's CORS defaults will allow the Tauri production origins in addition to the existing Vite origins.

The Tauri bundle will include the model and configuration under an `ai/` resource directory and enable both `nsis` and `msi` Windows targets. The result is one installer containing both the visible app and its hidden local service; the installer size is expected to exceed 500 MB.

## Build workflow

`scripts/build-backend-sidecar.ps1` will:

1. locate Conda using the same Windows fallback locations as the existing launcher;
2. verify that the `jazrielle-backend` environment exists and that the GGUF model is present;
3. run PyInstaller from that environment with the backend entrypoint;
4. place the executable at the exact Rust target-triple filename required by Tauri;
5. fail with an actionable message if the environment, PyInstaller, model, or output is missing.

The `tauri:dev` and `tauri:build` npm scripts will prepare the sidecar before invoking Tauri. A developer can run the Tauri app with one command after creating/updating the Conda environment; no manually started backend process is required for the Tauri workflow.

## Error handling

- Missing model: sidecar preparation fails before Tauri starts, with the expected model path in the message.
- Missing Conda environment or PyInstaller: sidecar preparation fails with the exact setup command needed.
- Sidecar spawn failure: Tauri returns an error during startup and does not expose a misleading ready state.
- Sidecar exits unexpectedly: Rust records the failure and the frontend's existing API error states remain visible; the process is not respawned in this first version.
- Browser development: no sidecar is started, and the existing Vite proxy behavior remains unchanged.

## Testing

- Backend unit test: the sidecar entrypoint accepts the default host/port and passes them to Uvicorn without importing a second app instance.
- Backend settings test: packaged asset environment paths override source-tree defaults.
- Frontend unit test: browser mode resolves `/api`, Tauri mode resolves the local backend URL, and an explicit `VITE_API_URL` wins.
- Rust unit tests: sidecar environment construction selects bundled resources first and development fallback resources second.
- Build verification: `npm run test:run`, `npm run typecheck`, `cargo check`, sidecar preparation, `npm run build`, and `npm run tauri:build` must pass. The generated NSIS/MSI artifacts will be checked under `src-tauri/target/release/bundle/`.

## Constraints

- The model file is already present locally but ignored by Git; release builders must provide it at `ai/qwen3-0.6b-q4_k_m.gguf` before building.
- Windows builds require Rust stable, WebView2, and a working Conda environment. MSI builds may additionally require the Windows VBScript optional feature; NSIS is the fallback installer target.
- The backend sidecar is local-only and binds to loopback; it must not be exposed on `0.0.0.0` by the packaged app.

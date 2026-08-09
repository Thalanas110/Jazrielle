# Standalone Tauri Installer Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build one Windows installer containing the Tauri UI, packaged FastAPI backend, local Qwen model, and configuration assets, with automatic backend startup and shutdown.

**Architecture:** PyInstaller creates a Windows sidecar from backend/sidecar.py. Tauri bundles that target-triple executable plus the ai directory and starts it through tauri-plugin-shell. The frontend uses /api in browsers and http://127.0.0.1:8000/api in Tauri.

**Tech Stack:** Python 3.11, FastAPI/Uvicorn, PyInstaller, React/Vite, TypeScript, Tauri 2, Rust, tauri-plugin-shell, NSIS, MSI.

## Global Constraints

- One installer contains the UI, backend, model, and prompt/action assets.
- The packaged backend binds only to 127.0.0.1:8000.
- The GGUF model is required at build time and is never committed to Git.
- Browser development keeps the Vite /api proxy.
- Generated executables and Rust output remain ignored.
- Windows target is x86_64-pc-windows-msvc.
- New runtime behavior follows failing-test-first development.

---

### Task 1: Prepare generated sidecar output

Files:
- Modify .gitignore
- Modify backend/environment.yml
- Create src-tauri/binaries/.gitkeep

- [ ] Add src-tauri/binaries/*.exe and .build/ to .gitignore.
- [ ] Add pyinstaller under the pip dependencies in backend/environment.yml.
- [ ] Create the empty .gitkeep.
- [ ] Run frontend: npm run test:run; expected 16 passing tests.
- [ ] Commit with message: build: prepare backend sidecar output.

### Task 2: Add and test the Python sidecar entrypoint

Files:
- Create backend/tests/test_sidecar.py
- Create backend/sidecar.py

Required interface:
    parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace
    run_server(argv: Sequence[str] | None = None, server_runner: Callable[..., Any] = uvicorn.run) -> None

- [ ] First add tests that assert parse_args([]) returns host 127.0.0.1 and port 8000, and that run_server(["--host", "127.0.0.1", "--port", "8011"], fake_runner) passes the application, host, port, and log_level warning to fake_runner.
- [ ] Run backend: pytest tests/test_sidecar.py -q; expected collection failure because sidecar.py is absent.
- [ ] Implement backend/sidecar.py with argparse, lazy import of app.main.app inside run_server, uvicorn.run, and the __main__ call.
- [ ] Run the focused test; expected 2 passing.
- [ ] Commit: feat: add packaged backend entrypoint.

### Task 3: Add packaged settings coverage

Files:
- Modify backend/tests/test_config.py
- Modify backend/app/core/config.py

- [ ] First add tests that set MODEL_PATH, SYSTEM_PROMPT_PATH, and ACTION_CONFIG_PATH with monkeypatch and assert Settings returns those absolute paths. Add a test asserting cors_origin_list includes tauri://localhost and http://tauri.localhost.
- [ ] Run backend: pytest tests/test_config.py -q; expected the Tauri-origin assertion fails.
- [ ] Add DEFAULT_CORS_ORIGINS in config.py with http://localhost:20380, http://127.0.0.1:20380, tauri://localhost, and http://tauri.localhost, and use it as the cors_origins default.
- [ ] Run config tests and commit: feat: support packaged backend assets.

### Task 4: Add deterministic Windows sidecar packaging

Files:
- Create scripts/build-backend-sidecar.ps1

Required behavior:
    Resolve the repository from PSScriptRoot.
    Require rustc host tuple x86_64-pc-windows-msvc.
    Require ai/qwen3-0.6b-q4_k_m.gguf.
    Locate conda.exe or USERPROFILE/anaconda3/Scripts/conda.exe from the existing Anaconda installation.
    Run conda run --no-capture-output -n jazrielle-backend python -m PyInstaller.
    Use --noconfirm --clean --onefile --noconsole --name jazrielle-backend --paths backend.
    Use --collect-all llama_cpp and --collect-all pycaw.
    Write dist output to src-tauri/binaries and rename jazrielle-backend.exe to jazrielle-backend-x86_64-pc-windows-msvc.exe.
    Throw on every missing prerequisite or nonzero build exit.

- [ ] Create the script with the exact paths and checks above.
- [ ] Run Get-Command powershell.exe and Test-Path ai/qwen3-0.6b-q4_k_m.gguf.
- [ ] Commit: build: add Windows backend sidecar builder.

### Task 5: Route production API calls to the sidecar

Files:
- Create frontend/src/lib/api-base.test.ts
- Modify frontend/src/lib/api.ts

Required interface:
    getApiBaseUrl(): string

- [ ] First add tests for browser mode returning /api and Tauri mode returning http://127.0.0.1:8000/api, using vi.stubGlobal.
- [ ] Run npm exec -- vitest run src/lib/api-base.test.ts; expected missing-export failure.
- [ ] Implement getApiBaseUrl using VITE_API_URL first, then isTauriRuntime() ? http://127.0.0.1:8000/api : /api. Replace all old API_BASE uses with calls to this helper.
- [ ] Run the focused test and npm run test:run.
- [ ] Commit: feat: route native API calls to local backend.

### Task 6: Add the Tauri shell plugin

Files:
- Modify src-tauri/Cargo.toml
- Modify src-tauri/Cargo.lock

- [ ] Add tauri-plugin-shell = "2" under dependencies.
- [ ] Run src-tauri: cargo check.
- [ ] Commit: build: add tauri shell plugin.

### Task 7: Add tested Rust resource helpers

Files:
- Create src-tauri/src/backend_runtime.rs
- Modify src-tauri/src/lib.rs
- Modify src-tauri/Cargo.toml

Required interfaces:
    select_asset_dir(resource_dir: &Path, development_asset_dir: &Path) -> Result<PathBuf, String>
    asset_environment(asset_dir: &Path) -> Vec<(String, String)>
    sidecar_name() -> &'static str

- [ ] Add tempfile = "3" under dev-dependencies.
- [ ] Write tests first for bundled ai preference, source ai fallback, four environment values, and stable sidecar name. The initial helper bodies must be todo!().
- [ ] Run cargo test backend_runtime; expected four failures from todo!().
- [ ] Implement bundled-first directory selection, asset paths for MODEL_PATH, SYSTEM_PROMPT_PATH, ACTION_CONFIG_PATH, CORS_ORIGINS, and return jazrielle-backend.
- [ ] Run cargo test backend_runtime.
- [ ] Commit: test: define packaged resource resolution.

### Task 8: Start and stop the sidecar from Tauri

Files:
- Modify src-tauri/src/lib.rs

Required behavior:
    Initialize tauri_plugin_shell.
    Select resource_dir/ai first and source-tree ../ai second.
    Set the four backend environment values before spawn.
    Spawn app.shell().sidecar("jazrielle-backend") with no user-controlled arguments.
    Store CommandChild inside BackendProcess(Mutex<Option<CommandChild>>).
    Drain sidecar events to stderr.
    Kill the child on RunEvent::Exit.

- [ ] Replace the current bare Builder with the lifecycle implementation above.
- [ ] Run cargo test and cargo check.
- [ ] Commit: feat: manage backend sidecar lifecycle.

### Task 9: Scope and bundle the sidecar and resources

Files:
- Modify src-tauri/capabilities/default.json
- Modify src-tauri/tauri.conf.json

- [ ] Add a shell:allow-execute permission limited to name binaries/jazrielle-backend, sidecar true, args [].
- [ ] Set bundle.active true, targets ["nsis", "msi"], externalBin ["binaries/jazrielle-backend"].
- [ ] Map ../ai/qwen3-0.6b-q4_k_m.gguf to ai/qwen3-0.6b-q4_k_m.gguf, ../ai/system-prompt.md to ai/system-prompt.md, and ../ai/assistant-actions.json to ai/assistant-actions.json.
- [ ] After a generated sidecar exists, run frontend: npm run tauri -- info.
- [ ] Commit: build: bundle backend in tauri installer.

### Task 10: Make Tauri commands self-contained

Files:
- Modify frontend/package.json
- Modify frontend/package-lock.json
- Modify README.md

- [ ] Add build:backend-sidecar invoking powershell -NoProfile -ExecutionPolicy Bypass -File ../scripts/build-backend-sidecar.ps1.
- [ ] Make tauri:dev and tauri:build run build:backend-sidecar before the existing root-launched Tauri commands.
- [ ] Document that frontend npm run tauri:dev is the one-command Tauri development workflow, and that no second backend terminal is required.
- [ ] Document one installer output under src-tauri/target/release/bundle and expected size over 500 MB.
- [ ] Commit: docs: automate standalone tauri workflow.

### Task 11: Add packaged sidecar smoke verification

Files:
- Create scripts/test-backend-sidecar.ps1

Required behavior:
    Resolve target triple and generated sidecar.
    Set MODEL_PATH, SYSTEM_PROMPT_PATH, ACTION_CONFIG_PATH, and CORS_ORIGINS to ai resources.
    Select an unused high port and start the sidecar hidden on 127.0.0.1.
    Poll /health for at most 15 seconds.
    Terminate the started process tree in a finally block.
    Assert the smoke-test port is free after shutdown.
    Throw if health never returns status ok.

- [x] Write the script with the behavior above.
- [x] Commit: test: add packaged backend smoke check.

### Task 12: Build and test the backend executable

- [x] Run conda env update -f backend/environment.yml --prune using the existing Anaconda installation.
- [x] Run frontend: npm run build:backend-sidecar.
- [x] Verify src-tauri/binaries/jazrielle-backend-x86_64-pc-windows-msvc.exe exists and remains ignored.
- [x] Run the smoke script from the repository root; expected Sidecar health check passed.
- [x] Do not commit the generated executable.

### Task 13: Test native startup and shutdown

- [ ] Run frontend: npm run tauri:dev.
- [ ] Verify one native orb appears, no backend terminal is opened, capabilities load, and a simple command returns.
- [ ] Close the app and verify Get-Process jazrielle-backend returns no process.
- [ ] Commit only source changes if lifecycle verification requires a fix.

### Task 14: Build the single installer

- [x] Run frontend: npm run tauri:build; rerun after final sidecar changes before merge.
- [x] Verify NSIS and MSI artifacts under src-tauri/target/release/bundle.
- [x] Inspect artifact sizes; both produced artifacts are approximately 509 MB with the model bundled.
- [x] Keep generated installers uncommitted.

### Task 15: Install and test the packaged application

- [ ] Run the generated *-setup.exe interactively.
- [ ] Launch the installed shortcut and verify orb, panel, backend capabilities, a command response, and no backend process after close.
- [ ] Uninstall from Windows Settings and verify only the installation directory is removed.

### Task 16: Final verification and documentation

Files:
- Modify README.md if final commands or paths differ.

- [x] Run frontend: npm run test:run and npm run build; run npm run typecheck before merge.
- [x] Run src-tauri: cargo test and cargo check.
- [x] Run scripts/test-backend-sidecar.ps1.
- [ ] Restore tracked frontend/dist/public if the build rewrites it.
- [x] Run git diff --check, git status --short, and git log --oneline --decorate -20.
- [x] Confirm no generated executable or installer is committed; generated frontend/dist changes remain local build output.
- [ ] Commit final documentation: docs: document standalone installer release.

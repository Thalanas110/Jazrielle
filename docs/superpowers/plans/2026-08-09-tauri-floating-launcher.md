# Tauri Floating Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing React/Vite Jazrielle interface into a Tauri v2 desktop assistant with a persistent always-on-top launcher circle and a bounded expanded panel.

**Architecture:** Keep React responsible for assistant state, API hooks, and content. Add a single transparent Tauri window that changes between launcher and panel dimensions, positions itself against the active monitor work area, and reports focus changes to React. Keep browser development working through a no-op native adapter and a centered panel fallback.

**Tech Stack:** React 19, TypeScript, Vite 6, Vitest 4, Testing Library, Three.js, Tauri v2, Rust 2021, FastAPI backend.

## Global Constraints

- Use one Tauri window; do not create a second launcher window.
- Collapsed window size is `80x80` logical pixels; expanded maximum is `420x640` logical pixels.
- The native window is transparent, borderless, always-on-top, non-resizable, and hidden from the Windows taskbar.
- Use `@tauri-apps/api` `2.11.1` and `@tauri-apps/cli` `2.11.4`.
- Use the Retro-Futuristic visual tokens `#0A0014`, `#00FFFF`, `#FF006E`, monospace display type, scanlines, and restrained glow.
- Preserve the existing assistant API hooks, backend action registry, and result metadata behavior.
- Do not add fabricated telemetry, fake identities, filler status strings, or arbitrary desktop automation.
- Write the test first for new behavior, verify the test fails for the expected reason, then implement the smallest passing code.
- End every task with the specified focused verification and commit.

---

### Task 1: Add frontend test and Tauri package foundations

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/test/setup.ts`

**Interfaces:**
- Produces `npm run test`, `npm run test:run`, and package access to `@tauri-apps/api`.

- [ ] **Step 1: Add dependencies and scripts**

Add runtime dependency `@tauri-apps/api: "^2.11.1"`, dev dependencies `@tauri-apps/cli: "^2.11.4"`, `@testing-library/jest-dom: "^6.6.3"`, `@testing-library/react: "^16.3.2"`, `jsdom: "^30.0.1"`, and `vitest: "^4.1.10"`. Add scripts:

```json
"test": "vitest",
"test:run": "vitest run --passWithNoTests",
"tauri": "tauri"
```

- [ ] **Step 2: Add Vitest configuration**

Create `frontend/vitest.config.ts` with React, the existing `@` alias, jsdom, globals, and setup file:

```ts
import path from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
```

- [ ] **Step 3: Add test setup**

Create `frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 4: Install and verify the harness**

Run `npm install` and `npm run test:run` from `frontend`.

Expected: Vitest exits successfully with zero test files collected.

- [ ] **Step 5: Commit**

```powershell
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/test/setup.ts
git commit -m "build: add frontend test and tauri dependencies"
```

### Task 2: Specify desktop geometry with failing tests

**Files:**
- Create: `frontend/src/lib/window-geometry.test.ts`

**Interfaces:**
- Consumes no production module yet.
- Produces expected behavior for `getWindowSize` and `getBottomRightPosition`.

- [ ] **Step 1: Write the failing test**

Create tests for the launcher and panel sizes and a 16px bottom-right inset using logical monitor work-area coordinates:

```ts
import { describe, expect, it } from 'vitest';
import { getBottomRightPosition, getWindowSize } from './window-geometry';

describe('window geometry', () => {
  it('returns the compact launcher size', () => {
    expect(getWindowSize('collapsed')).toEqual({ width: 80, height: 80 });
  });

  it('anchors the expanded panel above the bottom-right work-area inset', () => {
    expect(getBottomRightPosition({ x: 0, y: 0, width: 1920, height: 1040 }, 'expanded')).toEqual({ x: 1484, y: 384 });
  });
});
```

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/lib/window-geometry.test.ts`.

Expected: FAIL because `./window-geometry` does not exist.

- [ ] **Step 3: Commit the failing test**

```powershell
git add frontend/src/lib/window-geometry.test.ts
git commit -m "test: define floating window geometry"
```

### Task 3: Implement deterministic geometry math

**Files:**
- Create: `frontend/src/lib/window-geometry.ts`

**Interfaces:**
- Produces `WindowMode`, `WindowSize`, `WorkArea`, `WINDOW_SIZES`, `WINDOW_INSET`, `getWindowSize(mode)`, and `getBottomRightPosition(workArea, mode)`.

- [ ] **Step 1: Implement the minimal module**

Create the exact pure API used by Task 2:

```ts
export type WindowMode = 'collapsed' | 'expanded';
export type WindowSize = { width: number; height: number };
export type WorkArea = { x: number; y: number; width: number; height: number };

export const WINDOW_SIZES: Record<WindowMode, WindowSize> = {
  collapsed: { width: 80, height: 80 },
  expanded: { width: 420, height: 640 },
};

export const WINDOW_INSET = 16;

export function getWindowSize(mode: WindowMode): WindowSize {
  return WINDOW_SIZES[mode];
}

export function getBottomRightPosition(workArea: WorkArea, mode: WindowMode) {
  const size = getWindowSize(mode);
  return {
    x: workArea.x + workArea.width - size.width - WINDOW_INSET,
    y: workArea.y + workArea.height - size.height - WINDOW_INSET,
  };
}
```

- [ ] **Step 2: Run the focused test to verify GREEN**

Run `npm run test:run -- src/lib/window-geometry.test.ts`.

Expected: 2 tests pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/lib/window-geometry.ts
git commit -m "feat: add bottom-right window geometry"
```

### Task 4: Specify launcher state with failing tests

**Files:**
- Create: `frontend/src/lib/launcher-state.test.ts`

**Interfaces:**
- Produces reducer expectations for `collapsed`, `expanded`, and `toggle` actions.

- [ ] **Step 1: Write the failing tests**

```ts
import { describe, expect, it } from 'vitest';
import { launcherReducer, initialLauncherState } from './launcher-state';

describe('launcherReducer', () => {
  it('opens from collapsed state', () => {
    expect(launcherReducer(initialLauncherState, { type: 'open' })).toEqual({ mode: 'expanded' });
  });

  it('closes from expanded state', () => {
    expect(launcherReducer({ mode: 'expanded' }, { type: 'close' })).toEqual({ mode: 'collapsed' });
  });

  it('toggles the current mode', () => {
    expect(launcherReducer({ mode: 'collapsed' }, { type: 'toggle' }).mode).toBe('expanded');
    expect(launcherReducer({ mode: 'expanded' }, { type: 'toggle' }).mode).toBe('collapsed');
  });
});
```

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/lib/launcher-state.test.ts`.

Expected: FAIL because `./launcher-state` does not exist.

- [ ] **Step 3: Commit the failing test**

```powershell
git add frontend/src/lib/launcher-state.test.ts
git commit -m "test: define launcher state transitions"
```

### Task 5: Implement launcher state reducer

**Files:**
- Create: `frontend/src/lib/launcher-state.ts`

**Interfaces:**
- Produces `LauncherState`, `LauncherAction`, `initialLauncherState`, and `launcherReducer`.

- [ ] **Step 1: Implement the reducer**

```ts
import type { WindowMode } from './window-geometry';

export type LauncherState = { mode: WindowMode };
export type LauncherAction = { type: 'open' } | { type: 'close' } | { type: 'toggle' };

export const initialLauncherState: LauncherState = { mode: 'collapsed' };

export function launcherReducer(state: LauncherState, action: LauncherAction): LauncherState {
  if (action.type === 'open') return { mode: 'expanded' };
  if (action.type === 'close') return { mode: 'collapsed' };
  return { mode: state.mode === 'collapsed' ? 'expanded' : 'collapsed' };
}
```

- [ ] **Step 2: Run the focused test to verify GREEN**

Run `npm run test:run -- src/lib/launcher-state.test.ts`.

Expected: 3 tests pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/lib/launcher-state.ts
git commit -m "feat: add launcher state reducer"
```

### Task 6: Define the native adapter contract with failing tests

**Files:**
- Create: `frontend/src/lib/tauri-window.test.ts`

**Interfaces:**
- Produces the contract for `isTauriRuntime`, `getNativeWindowPort`, and `syncNativeWindow`.

- [ ] **Step 1: Write browser fallback tests**

Use `vi.stubGlobal('__TAURI_INTERNALS__', undefined)` and assert:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest';
import { isTauriRuntime, syncNativeWindow } from './tauri-window';

describe('tauri window adapter', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('detects browser development without native internals', () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);
    expect(isTauriRuntime()).toBe(false);
  });

  it('does not reject when geometry is requested in the browser', async () => {
    vi.stubGlobal('__TAURI_INTERNALS__', undefined);
    await expect(syncNativeWindow('collapsed')).resolves.toBe(false);
  });
});
```

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/lib/tauri-window.test.ts`.

Expected: FAIL because `./tauri-window` does not exist.

- [ ] **Step 3: Commit the failing test**

```powershell
git add frontend/src/lib/tauri-window.test.ts
git commit -m "test: define native window fallback"
```

### Task 7: Implement the Tauri window adapter

**Files:**
- Create: `frontend/src/lib/tauri-window.ts`

**Interfaces:**
- Consumes `getWindowSize`, `getBottomRightPosition`, and Tauri v2 window APIs.
- Produces `isTauriRuntime(): boolean` and `syncNativeWindow(mode: WindowMode): Promise<boolean>`.

- [ ] **Step 1: Implement the browser-safe adapter**

Use `getCurrentWindow`, `LogicalPosition`, `LogicalSize`, and `currentMonitor` only after checking `window.__TAURI_INTERNALS__`. Convert the monitor work area from physical to logical pixels using `monitor.scaleFactor`, then call `setSize`, `setPosition`, `setAlwaysOnTop(true)`, `setSkipTaskbar(true)`, and `setFocus()` for expanded mode. Return `false` in browser mode and `true` after native synchronization.

- [ ] **Step 2: Run adapter and all frontend tests**

Run `npm run test:run`.

Expected: all current tests pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/lib/tauri-window.ts
git commit -m "feat: add browser-safe tauri window adapter"
```

### Task 8: Scaffold the Tauri v2 Rust application

**Files:**
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/build.rs`
- Create: `src-tauri/src/main.rs`
- Create: `src-tauri/src/lib.rs`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/capabilities/default.json`

**Interfaces:**
- Produces a Tauri `main` window with the native desktop constraints from the spec.

- [ ] **Step 1: Add Rust package files**

Use Rust 2021 with `tauri = "2"`, `tauri-build = "2"`, `serde = "1"` with derive, and `serde_json = "1"`. The library exposes `run()` and the binary calls it.

- [ ] **Step 2: Add the Tauri configuration**

Use the following build and window values:

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Jazrielle",
  "version": "0.1.0",
  "identifier": "com.jazrielle.desktop",
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:20380",
    "frontendDist": "../frontend/dist/public"
  },
  "app": {
    "windows": [{
      "label": "main",
      "title": "Jazrielle",
      "width": 80,
      "height": 80,
      "minWidth": 80,
      "minHeight": 80,
      "maxWidth": 420,
      "maxHeight": 640,
      "resizable": false,
      "decorations": false,
      "transparent": true,
      "alwaysOnTop": true,
      "skipTaskbar": true,
      "visible": false,
      "shadow": false,
      "center": false
    }]
  },
  "bundle": { "active": false }
}
```

- [ ] **Step 3: Add window permissions**

Give the `main` window `core:window:default` permission in `src-tauri/capabilities/default.json` so the adapter can use window resize, position, focus, visibility, topmost, and taskbar operations.

- [ ] **Step 4: Verify Rust compilation**

Run `cargo check` from `src-tauri`.

Expected: Cargo resolves Tauri v2 and exits with code 0.

- [ ] **Step 5: Commit**

```powershell
git add src-tauri
git commit -m "feat: scaffold tauri desktop shell"
```

### Task 9: Add Tauri scripts and metadata checks

**Files:**
- Modify: `frontend/package.json`
- Modify: `README.md`

**Interfaces:**
- Produces `npm run tauri:dev` and `npm run tauri:build` entry points.

- [ ] **Step 1: Add scripts**

Add:

```json
"tauri:dev": "tauri dev --config ../src-tauri/tauri.conf.json",
"tauri:build": "tauri build --config ../src-tauri/tauri.conf.json"
```

These commands are run from `frontend`, so the Tauri configuration uses `npm run dev` and `npm run build` as its `beforeDevCommand` and `beforeBuildCommand` values.

- [ ] **Step 2: Document desktop startup**

Add a Tauri section to `README.md` that starts the backend, runs `npm run tauri:dev` from `frontend`, and names the expected launcher/panel behavior.

- [ ] **Step 3: Verify script resolution**

Run `npm run tauri -- --version` from `frontend`.

Expected: the command prints the installed Tauri CLI version and does not start an app.

- [ ] **Step 4: Commit**

```powershell
git add frontend/package.json README.md
git commit -m "docs: add tauri development commands"
```

### Task 10: Add the reusable floating launcher component with failing tests

**Files:**
- Create: `frontend/src/components/floating-launcher.test.tsx`
- Create: `frontend/src/components/floating-launcher.tsx`

**Interfaces:**
- Produces `FloatingLauncher` props `{ active: boolean; thinking: boolean; onOpen: () => void }`.

- [ ] **Step 1: Write the failing component test**

Render the component and assert a button named `Open Jazrielle` calls `onOpen`, and the thinking state adds `data-state="thinking"`.

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/components/floating-launcher.test.tsx`.

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Commit the failing test**

```powershell
git add frontend/src/components/floating-launcher.test.tsx
git commit -m "test: define floating launcher component"
```

### Task 11: Implement the floating launcher component

**Files:**
- Create: `frontend/src/components/floating-launcher.tsx`

**Interfaces:**
- Consumes the props from Task 10.
- Produces an accessible circular button with the existing `OrbCanvas` supplied as a child render area.

- [ ] **Step 1: Implement the minimal component**

Render a `button` with `type="button"`, `aria-label="Open Jazrielle"`, `data-testid="button-open-launcher"`, `data-state`, and a visual orb slot. Keep it presentational so geometry and API behavior stay in the parent.

- [ ] **Step 2: Run the focused test to verify GREEN**

Run `npm run test:run -- src/components/floating-launcher.test.tsx`.

Expected: 2 assertions pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/components/floating-launcher.tsx
git commit -m "feat: add persistent floating launcher"
```

### Task 12: Add the panel wrapper with failing tests

**Files:**
- Create: `frontend/src/components/assistant-panel.test.tsx`
- Create: `frontend/src/components/assistant-panel.tsx`

**Interfaces:**
- Produces `AssistantPanel` props `{ onClose: () => void; children: ReactNode }`.

- [ ] **Step 1: Write the failing test**

Assert the panel renders a `role="dialog"` with accessible name `Jazrielle assistant`, a close button named `Close Jazrielle`, and invokes `onClose`.

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/components/assistant-panel.test.tsx`.

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Commit the failing test**

```powershell
git add frontend/src/components/assistant-panel.test.tsx
git commit -m "test: define bounded assistant panel"
```

### Task 13: Implement the bounded panel wrapper

**Files:**
- Create: `frontend/src/components/assistant-panel.tsx`

**Interfaces:**
- Consumes panel props from Task 12.
- Produces a semantic dialog shell with a close control and content slot.

- [ ] **Step 1: Implement the wrapper**

Use a `<section role="dialog" aria-modal="false" aria-labelledby="assistant-panel-title">`, an `h1` with `Jazrielle`, a close button with `aria-label="Close Jazrielle"`, and a content slot.

- [ ] **Step 2: Run the focused test to verify GREEN**

Run `npm run test:run -- src/components/assistant-panel.test.tsx`.

Expected: all panel assertions pass.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/components/assistant-panel.tsx
git commit -m "feat: add bounded assistant panel shell"
```

### Task 14: Wire native geometry and focus behavior

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/tauri-window.ts`
- Create: `frontend/src/lib/use-launcher-window.ts`
- Create: `frontend/src/lib/use-launcher-window.test.ts`

**Interfaces:**
- `useLauncherWindow(mode, onClose)` initializes the native window, synchronizes sizes, listens for `onFocusChanged`, and handles browser document outside-click and Escape.

- [ ] **Step 1: Write failing hook behavior tests**

Test the browser fallback with `renderHook`: changing mode calls the adapter with the matching mode; `Escape` calls `onClose`; a document pointer event outside the supplied root calls `onClose`.

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/lib/use-launcher-window.test.ts`.

Expected: FAIL because the hook does not exist.

- [ ] **Step 3: Implement the hook**

The hook should:

```ts
useEffect(() => { void syncNativeWindow(mode); }, [mode]);
useEffect(() => { /* Escape and browser outside-click listeners */ }, [onClose]);
```

In Tauri mode, register `getCurrentWindow().onFocusChanged` and call `onClose` only when the panel is expanded and the payload is false. On initialization, sync the collapsed window and call `show()` in the native runtime.

- [ ] **Step 4: Wire `Home` to launcher state**

Replace the current full-page root with a `useReducer(launcherReducer, initialLauncherState)`. Render `FloatingLauncher` when collapsed and `AssistantPanel` containing the existing assistant surface when expanded. Pass the command pending state to the launcher.

- [ ] **Step 5: Run all frontend tests and typecheck**

Run `npm run test:run` and `npm run typecheck` from `frontend`.

Expected: all tests pass and TypeScript exits 0.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/lib/tauri-window.ts frontend/src/lib/use-launcher-window.ts frontend/src/lib/use-launcher-window.test.ts
git commit -m "feat: connect launcher state to native window"
```

### Task 15: Refactor assistant content into a compact panel body

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/assistant-content.tsx`

**Interfaces:**
- Produces `AssistantContent` with the current command, inference, history, capability, and result behavior passed through typed props or existing hooks.

- [ ] **Step 1: Extract the assistant body without changing behavior**

Move the existing command/inference/history/capability JSX and handlers into `AssistantContent`. Keep `OrbCanvas` available to both the compact launcher and panel header. Preserve all existing `data-testid` hooks for command, inference, result, error, history, and capabilities.

- [ ] **Step 2: Run regression checks**

Run `npm run test:run`, `npm run typecheck`, and `npm run build` from `frontend`.

Expected: all tests pass, typecheck passes, and Vite builds.

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/components/assistant-content.tsx
git commit -m "refactor: isolate compact assistant content"
```

### Task 16: Replace the existing visual system with Retro-Futuristic tokens

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/index.html`

**Interfaces:**
- Produces CSS tokens and selectors for transparent native root, launcher, bounded panel, scanlines, neon signal colors, responsive browser fallback, and reduced motion.

- [ ] **Step 1: Remove the current warm-teal/Manrope font imports**

Replace Google font imports with period-specific families and fallbacks:

```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');
```

Set the root tokens to `#0A0014`, `#00FFFF`, and `#FF006E`; keep every declared font mono-compatible for the chosen anchor.

- [ ] **Step 2: Add the transparent desktop root and scanline texture**

Use `html, body, #root { min-height: 100%; background: transparent; }`, an `.app-frame::before` scanline overlay with `repeating-linear-gradient`, and `pointer-events: none` on purely decorative layers.

- [ ] **Step 3: Add visual selectors**

Style `.launcher-button`, `.launcher-orb`, `.assistant-panel`, `.assistant-panel::before`, `.panel-header`, `.command-form`, `.quick-chip`, `.notice`, `.panel`, and `.capability-drawer` with crisp borders, neon glow, no full-page margins, and max dimensions matching the Tauri window.

- [ ] **Step 4: Add reduced motion**

Under `@media (prefers-reduced-motion: reduce)`, set animation and transition durations to `0.01ms`, iteration count to `1`, and remove orb scaling.

- [ ] **Step 5: Build to catch CSS and HTML regressions**

Run `npm run typecheck` and `npm run build`.

Expected: both exit 0.

- [ ] **Step 6: Commit**

```powershell
git add frontend/src/index.css frontend/index.html
git commit -m "style: establish retro futuristic visual system"
```

### Task 17: Adapt the orb for the launcher and panel states

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/floating-launcher.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Produces a shared assistant presence visual that is readable at launcher size and still supports active/thinking state in the panel.

- [ ] **Step 1: Add a compact orb render path**

Keep the existing Three.js canvas for the expanded panel and add CSS-driven ring layers for the 80px launcher. The launcher must render without requiring a `190x190` canvas.

- [ ] **Step 2: Apply Retro-Futuristic signal behavior**

Use cyan as the primary ring, magenta as the offset ring, and a stronger glow while command or inference mutations are pending. Keep the fallback 2D animation functional.

- [ ] **Step 3: Run regression checks**

Run `npm run test:run`, `npm run typecheck`, and `npm run build`.

Expected: all checks pass.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/components/floating-launcher.tsx frontend/src/index.css
git commit -m "feat: adapt orb for launcher presence"
```

### Task 18: Preserve browser fallback behavior

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/lib/use-launcher-window.ts`
- Create: `frontend/src/components/assistant-shell.test.tsx`

**Interfaces:**
- Produces a browser-only shell that starts expanded or centered for Vite preview without Tauri internals.

- [ ] **Step 1: Write the failing fallback integration test**

Render the shell with Tauri internals absent and assert the panel is visible in browser mode, the launcher button is not used as the only content, and Escape returns to the launcher state.

- [ ] **Step 2: Run the focused test to verify RED**

Run `npm run test:run -- src/components/assistant-shell.test.tsx`.

Expected: FAIL until the browser fallback state is wired.

- [ ] **Step 3: Implement browser fallback**

Start browser mode expanded so existing Vite development remains useful. Keep native mode collapsed on first render until the initial native sync completes. Use the hook's document listeners for outside click and Escape only in browser mode.

- [ ] **Step 4: Run focused and full frontend checks**

Run `npm run test:run`, `npm run typecheck`, and `npm run build`.

Expected: all checks pass.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/App.tsx frontend/src/index.css frontend/src/lib/use-launcher-window.ts frontend/src/components/assistant-shell.test.tsx
git commit -m "test: preserve browser launcher fallback"
```

### Task 19: Add native startup visibility and capability hardening

**Files:**
- Modify: `frontend/src/lib/tauri-window.ts`
- Modify: `src-tauri/capabilities/default.json`
- Modify: `src-tauri/tauri.conf.json`

**Interfaces:**
- Produces a native startup sequence that sets topmost/taskbar state, positions the collapsed launcher, then shows the window.

- [ ] **Step 1: Add an explicit initialization function**

Add `initializeNativeWindow(): Promise<boolean>` that returns false in browser mode and, in Tauri mode, calls `setAlwaysOnTop(true)`, `setSkipTaskbar(true)`, `syncNativeWindow('collapsed')`, and `show()` in that order.

- [ ] **Step 2: Add only required permissions**

Keep `core:window:default` for the main window and ensure the capability scope lists only `main`.

- [ ] **Step 3: Verify native compilation**

Run `cargo check` from `src-tauri`.

Expected: exit 0.

- [ ] **Step 4: Commit**

```powershell
git add frontend/src/lib/tauri-window.ts src-tauri/capabilities/default.json src-tauri/tauri.conf.json
git commit -m "feat: initialize native launcher visibility"
```

### Task 20: Add accessibility and keyboard regression coverage

**Files:**
- Modify: `frontend/src/components/floating-launcher.test.tsx`
- Modify: `frontend/src/components/assistant-panel.test.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Produces tested accessible names, focus-visible styles, and reduced motion behavior.

- [ ] **Step 1: Add failing assertions**

Assert the launcher is keyboard focusable, the panel close control is reachable by role/name, and focus-visible styles are present through the rendered class contract.

- [ ] **Step 2: Run focused tests to verify RED**

Run `npm run test:run -- src/components/floating-launcher.test.tsx src/components/assistant-panel.test.tsx`.

Expected: the new assertions fail before the accessibility adjustments.

- [ ] **Step 3: Implement focus and motion styling**

Add `:focus-visible` outlines using cyan, ensure buttons have visible labels, and keep reduced motion rules from Task 16.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run the same focused test command.

Expected: all focused tests pass.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/components/floating-launcher.test.tsx frontend/src/components/assistant-panel.test.tsx frontend/src/index.css
git commit -m "fix: harden launcher keyboard accessibility"
```

### Task 21: Update project documentation and ignore rules

**Files:**
- Modify: `README.md`
- Modify: `.gitignore`

**Interfaces:**
- Documents Tauri prerequisites, launch commands, native/browser behavior, and the ignored `src-tauri/target` output.

- [ ] **Step 1: Document prerequisites and behavior**

Document Rust stable, WebView2 on Windows, the backend startup, `npm run tauri:dev`, `npm run tauri:build`, the 80px launcher, the 420x640 panel cap, and the browser fallback.

- [ ] **Step 2: Add native build outputs to ignore rules**

Add `src-tauri/target/` and any generated Tauri bundle output while preserving existing ignore patterns.

- [ ] **Step 3: Verify documentation diff**

Run `git diff --check` and inspect `git status --short`.

- [ ] **Step 4: Commit**

```powershell
git add README.md .gitignore
git commit -m "docs: document floating tauri assistant"
```

### Task 22: Run full verification and make the final test commit

**Files:**
- Modify only files required by verification failures.

**Interfaces:**
- Produces a verified feature branch with frontend, native, and backend verification evidence.

- [ ] **Step 1: Run frontend test suite**

From `frontend`, run `npm run test:run`.

Expected: all tests pass with zero failures.

- [ ] **Step 2: Run frontend typecheck and build**

Run `npm run typecheck` and `npm run build`.

Expected: both exit 0. The existing Vite chunk-size warning may remain because it is unrelated to this feature.

- [ ] **Step 3: Run Tauri compilation**

From `src-tauri`, run `cargo check`.

Expected: exit 0. If native dependencies are missing, record the exact toolchain error instead of masking it.

- [ ] **Step 4: Run backend tests**

From `backend`, run `pytest -q` using the project’s configured Python environment.

Expected: existing backend tests pass. If `pytest`/Conda remains unavailable, report that environment limitation explicitly.

- [ ] **Step 5: Run manual desktop verification when Tauri runtime is available**

Run `npm run tauri:dev` from `frontend` and verify:

1. startup shows only the launcher circle;
2. the circle stays above another window;
3. clicking it opens the bounded panel from the same corner;
4. command input receives focus;
5. Escape, close, and focus loss collapse it;
6. an API error leaves the panel open with retry available.

- [ ] **Step 6: Commit verification evidence**

If code or tests needed a final correction, run the affected focused test again, then commit:

```powershell
git add frontend src-tauri README.md .gitignore
git commit -m "test: verify floating tauri launcher"
```

If no correction was needed, create the same commit only after adding a small verification note to `docs/superpowers/plans/2026-08-09-tauri-floating-launcher.md` with the observed command outputs.

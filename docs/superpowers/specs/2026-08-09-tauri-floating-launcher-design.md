# Tauri Floating Launcher and Bounded Jarvis Panel

## Context

Jazrielle currently runs as a React/Vite browser interface backed by FastAPI. The repository has no `src-tauri` application yet. The requested desktop behavior is a persistent floating circle that stays above the Windows desktop and expands into a bounded Jarvis panel from the same location.

The work covers the native desktop shell and the frontend redesign needed to make the existing assistant UI fit inside that interaction. Existing backend endpoints and assistant action semantics remain unchanged.

## Goal

Create a single-window Tauri desktop experience in which:

1. The app launches as a small floating circular launcher.
2. The launcher stays above other desktop windows and remains available.
3. Clicking the launcher expands the interface into a bounded panel anchored from the launcher position.
4. Closing the panel, pressing `Esc`, or losing native window focus collapses it back to the circle.
5. The existing command, inference, history, capability, loading, result, and error behaviors remain usable.

## Visual direction

Use a Retro-Futuristic visual anchor. The surface is deep navy-black `#0A0014` with cyan `#00FFFF` and magenta `#FF006E` as the signal colors. Typography uses period-specific monospace families such as `Space Mono` and `IBM Plex Mono`, with bundled or system fallbacks. CRT scanlines, restrained neon glow, and chromatic offset provide texture without turning the assistant into a decorative dashboard.

The persistent launcher is the visual nucleus: a breathing cyan ring with a subtle magenta offset. In the expanded state the same orb remains docked to the panel edge, making the panel feel like it unfolds from the launcher.

Content stays grounded in existing product information. Keep real assistant labels, action results, capability names, errors, and controls. Do not add fabricated telemetry, fake session identities, filler status copy, or themed replacements for ordinary actions.

## Native architecture

Add a Tauri v2 application under `src-tauri` at the repository root around the existing `frontend` package.

Use one transparent, borderless, always-on-top native window:

- collapsed size: approximately `80x80px`;
- expanded maximum size: approximately `420x640px`;
- fixed near the bottom-right desktop edge with a safe inset from the taskbar;
- non-resizable and omitted from the taskbar;
- transparent outside the visible circle or panel surface;
- focused when expanded so keyboard input works.

The frontend calls a narrow geometry helper for the native window. The helper is responsible for detecting the Tauri environment, resizing and repositioning the window, and providing a browser fallback. The native layer owns desktop presence and geometry; React owns assistant state and API interactions.

The Tauri configuration must support the existing frontend layout:

- development command runs the Vite app from `frontend`;
- production build uses `frontend/dist/public`;
- the existing Vite port and backend proxy remain the development defaults;
- no backend API contract changes are required.

## Frontend structure

Refactor the current `Home` surface into focused units where useful, while keeping the existing API hooks:

- `FloatingLauncher`: collapsed circular trigger, readiness/thinking state, accessible label;
- `AssistantPanel`: bounded expanded shell and close control;
- `AssistantOrb`: existing Three.js orb behavior adapted to the new compact surface;
- `CommandSurface`: command input, submit button, quick commands, loading state;
- `ActivityPanels`: recent command history and local inference surface;
- `CapabilitiesDrawer`: existing capability disclosure behavior;
- `window-geometry` helper: Tauri detection, size/position transitions, browser fallback.

The panel should be compact enough to fit the maximum bounds without requiring a full-page layout. Keep the command input prominent, reduce decorative shell copy, and preserve the existing result and error feedback.

## Interaction state and data flow

Use a small UI state model:

- `collapsed`: native window is launcher-sized and only the circle is rendered;
- `expanded`: native window is panel-sized and the command input receives focus;
- `thinking`: derived from command or inference mutation pending state and drives orb motion;
- `error`: derived from existing mutation errors and keeps the panel open for retry.

On launcher click:

1. set the React state to `expanded`;
2. request the expanded native size and anchored position;
3. focus the command input after the panel is available.

On close, `Esc`, or native focus loss:

1. set the React state to `collapsed`;
2. request the launcher size and bottom-right position;
3. return focus to the launcher when possible.

Command submission continues through the existing `useExecuteJarvisCommand` hook. Results append to history, retain application or URL metadata, and use the existing native/browser launch boundary. Inference continues through `useRunJarvisInference`. No model prompt or backend action registry changes are part of this work.

When the Tauri bridge is unavailable, the browser build renders the expanded panel in a normal centered stage and uses document-level outside-click handling. This preserves Vite development and frontend verification without requiring the desktop shell.

## Error handling and accessibility

- Native geometry failures must not crash the assistant; the UI should retain its current state and report only actionable errors.
- Backend errors remain visible inside the panel with the existing retry action.
- A failed command does not collapse the panel.
- The launcher and every icon-only control have accessible labels.
- Keyboard users can open the launcher, use the command input, submit with Enter, and collapse with Escape.
- Motion respects `prefers-reduced-motion`; reduced mode removes scanline movement, breathing scale, and nonessential transitions.
- The transparent native window must not capture desktop clicks outside its visible content beyond normal window focus behavior.

## Acceptance criteria

1. The Tauri app launches showing only the floating circle.
2. The circle stays above other Windows applications and is not represented as a taskbar button.
3. Clicking the circle opens the bounded panel anchored from the same desktop position.
4. The panel never exceeds its configured maximum dimensions.
5. Close, Escape, and native focus loss return to the launcher state.
6. The command input, quick commands, history, inference, capabilities, loading, result, and error flows remain functional.
7. Browser development remains usable without Tauri APIs.
8. Frontend typecheck and production build pass.
9. Tauri compilation/checking passes when the Rust toolchain is available.
10. Existing backend tests remain unaffected and pass when run.

## Verification plan

Run the following checks after implementation:

- `npm run typecheck` from `frontend`;
- `npm run build` from `frontend`;
- `cargo check` from `src-tauri`;
- `pytest -q` from `backend`;
- manual desktop verification of launcher persistence, expansion geometry, focus loss, Escape, close, and API error states.

## Scope boundaries

This change does not add arbitrary desktop automation, modify the assistant action registry, replace the FastAPI service, or invent a new native launch protocol. It establishes the Tauri window shell and the frontend presentation/interaction needed for the floating Jarvis surface.

# Dynamic project discovery design

Date: 2026-08-09

## Goal

Replace the manually maintained project list in `ai/assistant-actions.json` with automatic discovery of Git repositories below the configured development root. Users should be able to ask Jazrielle to open VS Code for a project without editing the assistant configuration for every new repository.

## Scope

In scope:

- recursively discover Git repositories below `settings.projectRoot`;
- keep every discovered working directory inside that root;
- skip dependency, metadata, and worktree directories during discovery;
- generate stable project identifiers from repository names and relative paths;
- expose discovered identifiers to command capabilities and model context;
- launch every project with the same fixed VS Code command;
- test discovery, exclusions, duplicate names, safety boundaries, and command selection.

Out of scope:

- Tauri or another native frontend wrapper;
- arbitrary model-supplied paths or executable commands;
- automatic discovery outside the configured root;
- changing application allowlisting for Calendar, Downloads, or Spotify.

## Configuration

`ai/assistant-actions.json` keeps `settings.projectRoot` as the single project boundary. The `projects` object becomes empty by default; the loader populates it from repositories discovered below that root.

Each discovered project receives a fixed target:

```text
command: cmd.exe /d /s /c "code.cmd ."
process: Code.exe
working directory: discovered repository root
```

The command is application-owned and never comes from the model or a project directory.

## Discovery algorithm

1. Resolve `projectRoot` relative to the action configuration file and require that it exists as a directory.
2. Walk descendants of the root recursively.
3. Treat a directory as a project when it contains a `.git` directory or `.git` file.
4. Prune `.git`, `.worktrees`, `node_modules`, and hidden directories from traversal. This avoids scanning Git internals, generated worktrees, dependency trees, and metadata repositories.
5. Resolve each repository path and verify it is relative to the resolved project root.
6. Use the repository folder name as its identifier when that name is unique. For duplicate names, use the normalized relative path from the project root so the targets remain unambiguous.
7. Store only discovered target metadata in the runtime action configuration; do not write generated projects back to disk.

The discovery result is deterministic for a given filesystem. Sorting by normalized relative path keeps capability order stable.

## Model and capability context

The canonical safety and action rules remain in `ai/system-prompt.md`. The assistant service appends a generated project-target context for command interpretation, containing only discovered identifiers. This lets the model select `start_project` without hardcoding repository names in the canonical prompt.

The action registry also generates `start_project` capability examples from the discovered identifiers. The model argument must match one of those identifiers; the backend resolves it only through the discovered registry.

## Safety and errors

- A missing or invalid project root prevents configuration from loading.
- A discovered path outside the resolved root is rejected.
- A model-supplied project name that is not discovered returns the existing handled-false result.
- No model value is used as a filesystem path, executable, or command array.
- The fixed command runs with `shell=False` through the existing process adapter.
- Tauri remains a later integration for browser-to-desktop application launching; it is not part of this change.

## Verification

Tests will cover:

- nested Git repository discovery;
- `.git` file repositories;
- exclusion of `node_modules`, hidden directories, and `.worktrees`;
- duplicate repository names and relative-path identifiers;
- rejection of paths outside the root;
- generated capability examples and prompt context;
- fixed VS Code command and configured working directory;
- full backend regression coverage.

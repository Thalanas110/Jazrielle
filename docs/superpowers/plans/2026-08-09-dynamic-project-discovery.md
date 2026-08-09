# Dynamic Project Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Discover Git projects recursively under the configured development root so Jazrielle can open VS Code for new projects without a hardcoded project list.

**Architecture:** A focused filesystem helper discovers repository roots and returns stable identifiers. The action-config loader turns those paths into fixed `ProjectTarget` entries under the existing root boundary. The assistant service appends discovered identifiers to the canonical prompt only for command interpretation, while the action registry exposes matching capability examples.

**Tech Stack:** Python 3.11, FastAPI service layer, Pydantic models, `os.walk`, pytest, JSON configuration, Markdown documentation.

## Global Constraints

- Discover only Git repositories below `settings.projectRoot`.
- Skip `.git`, `.worktrees`, `node_modules`, and hidden directories while walking.
- Use the repository folder name when unique; use its normalized relative path when names collide.
- Use the fixed command `cmd.exe /d /s /c "code.cmd ."` and process name `Code.exe` for every discovered project.
- Never use a model value as a filesystem path, executable, or command array.
- Keep Tauri and other native frontend wrappers out of this change.
- Preserve application allowlisting for Calendar, Downloads, and Spotify.

---

### Task 1: Add the repository discovery helper

**Files:**
- Create: `backend/app/modules/assistant/project_discovery.py`
- Create: `backend/tests/test_project_discovery.py`

**Interfaces:**
- Produces `discover_project_directories(project_root: Path) -> dict[str, Path]`.
- The result is sorted by normalized relative path and contains only paths inside the resolved root.

- [ ] **Step 1: Write the failing discovery tests**

Create temporary repositories by creating either a `.git` directory or a `.git` file. Cover nested repositories, duplicate names, and excluded trees:

```python
def mark_repository(path: Path, *, git_file: bool = False) -> None:
    path.mkdir(parents=True)
    marker = path / ".git"
    if git_file:
        marker.write_text("gitdir: ../.git/worktrees/demo", encoding="utf-8")
    else:
        marker.mkdir()


def test_discover_project_directories_finds_nested_git_repositories(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "business" / "alpha")
    mark_repository(root / "personal" / "beta", git_file=True)

    assert discover_project_directories(root) == {
        "alpha": (root / "business" / "alpha").resolve(),
        "beta": (root / "personal" / "beta").resolve(),
    }


def test_discover_project_directories_uses_relative_paths_for_duplicate_names(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "one" / "shared")
    mark_repository(root / "two" / "shared")

    assert discover_project_directories(root) == {
        "one/shared": (root / "one" / "shared").resolve(),
        "two/shared": (root / "two" / "shared").resolve(),
    }


def test_discover_project_directories_prunes_dependencies_hidden_dirs_and_worktrees(tmp_path):
    root = tmp_path / "development"
    mark_repository(root / "valid")
    mark_repository(root / "valid" / "node_modules" / "dependency")
    mark_repository(root / "valid" / ".worktrees" / "branch")
    mark_repository(root / "valid" / ".metadata" / "hidden")

    assert discover_project_directories(root) == {
        "valid": (root / "valid").resolve(),
    }
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run from `backend`:

```powershell
$backendPython = Join-Path $env:USERPROFILE 'anaconda3\\envs\\jazrielle-backend\\python.exe'
& $backendPython -m pytest -q tests/test_project_discovery.py
```

Expected: FAIL because `project_discovery.py` and `discover_project_directories` do not exist.

- [ ] **Step 3: Write the minimal discovery helper**

Implement a standard-library-only walker:

```python
import os
from collections import Counter
from pathlib import Path


_PRUNED_DIRECTORY_NAMES = {".git", ".worktrees", "node_modules"}


def discover_project_directories(project_root: Path) -> dict[str, Path]:
    root = project_root.resolve()
    candidates: list[tuple[Path, Path]] = []

    for current, directories, _files in os.walk(root, topdown=True):
        current_path = Path(current).resolve()
        directories[:] = sorted(
            name
            for name in directories
            if name not in _PRUNED_DIRECTORY_NAMES and not name.startswith(".")
        )
        marker = current_path / ".git"
        if current_path != root and (marker.is_dir() or marker.is_file()):
            candidates.append((current_path.relative_to(root), current_path))
            directories[:] = []

    candidates.sort(key=lambda item: item[0].as_posix().casefold())
    name_counts = Counter(relative.name.casefold() for relative, _path in candidates)
    discovered: dict[str, Path] = {}
    for relative, path in candidates:
        name = relative.name.casefold()
        identifier = name if name_counts[name] == 1 else relative.as_posix().casefold()
        if not path.is_relative_to(root):
            raise ValueError(f"Discovered project is outside the project root: {path}")
        discovered[identifier] = path
    return discovered
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run the same pytest command. Expected: all discovery tests PASS.

- [ ] **Step 5: Commit the helper and tests**

```powershell
git add backend/app/modules/assistant/project_discovery.py backend/tests/test_project_discovery.py
git commit -m "feat: discover git projects under configured root"
```

### Task 2: Integrate discovery into action configuration

**Files:**
- Modify: `backend/app/modules/assistant/action_config.py`
- Modify: `ai/assistant-actions.json`
- Modify: `backend/tests/test_action_config.py`
- Modify: `backend/tests/test_process_actions.py`

**Interfaces:**
- Consumes `discover_project_directories(project_root)` from Task 1.
- Produces `AssistantActionConfig.projects` entries with `ProjectTarget.working_directory`, fixed `start_command`, and `Code.exe` process name.

- [ ] **Step 1: Write the failing loader and handler assertions**

Require an empty JSON `projects` object to discover repositories dynamically:

```python
def test_default_projects_are_discovered_with_fixed_vscode_targets():
    config = load_action_config(DEFAULT_ACTION_CONFIG_PATH)

    assert config.projects["jazrielle"].working_directory.name == "jazrielle"
    assert config.projects["jazrielle"].start_command == [
        "cmd.exe", "/d", "/s", "/c", "code.cmd ."
    ]
    assert config.projects["jazrielle"].process_name == "Code.exe"
```

- [ ] **Step 2: Run the focused configuration tests and verify failure**

```powershell
& $backendPython -m pytest -q tests/test_action_config.py tests/test_process_actions.py
```

Expected: the existing manually populated configuration does not yet discover from an empty project map.

- [ ] **Step 3: Implement loader integration**

In `load_action_config`, resolve and validate `projectRoot`, then populate an empty configured project map from discovery:

```python
config.settings.project_root = _resolve_existing_directory(
    config.settings.project_root, base_dir
)
if not config.projects:
    config.projects = {
        identifier: ProjectTarget(
            workingDirectory=path,
            startCommand=["cmd.exe", "/d", "/s", "/c", "code.cmd ."],
            processName="Code.exe",
        )
        for identifier, path in discover_project_directories(config.settings.project_root).items()
    }
for project_name, project in config.projects.items():
    project.working_directory = _resolve_existing_directory(project.working_directory, base_dir)
    if not project.working_directory.is_relative_to(config.settings.project_root):
        raise ConfigError(f"Configured project outside the configured project root: {project_name}")
```

Keep explicit project entries supported for isolated tests and intentional overrides, but use `"projects": {}` in the repository configuration.

- [ ] **Step 4: Remove the hardcoded repository entries from JSON**

Keep only the root boundary in the repository config:

```json
"projects": {},
"settings": {
  "projectRoot": "../../../",
  "reminderPath": "reminders.json",
  "weatherLocation": "Manila, Philippines",
  "repositoryPath": ".."
}
```

- [ ] **Step 5: Run configuration and process tests**

```powershell
& $backendPython -m pytest -q tests/test_action_config.py tests/test_process_actions.py
```

Expected: all focused tests PASS without launching VS Code; process tests use the fake adapter.

- [ ] **Step 6: Commit configuration integration**

```powershell
git add backend/app/modules/assistant/action_config.py ai/assistant-actions.json backend/tests/test_action_config.py backend/tests/test_process_actions.py
git commit -m "feat: populate project targets from discovery"
```

### Task 3: Provide discovered project context to model commands

**Files:**
- Modify: `backend/app/modules/assistant/action_registry.py`
- Modify: `backend/app/modules/assistant/service.py`
- Modify: `ai/system-prompt.md`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/test_modules.py`

**Interfaces:**
- `ActionRegistry` stores optional project identifiers and exposes `get_project_prompt_context() -> str`.
- `AssistantService.execute_command` sends the canonical prompt plus generated project context.

- [ ] **Step 1: Write failing context tests**

Add a service test that captures the system prompt:

```python
@pytest.mark.anyio
async def test_execute_command_appends_discovered_project_context():
    provider = ConfiguredProvider()
    provider.response = '{"action":"conversation","arguments":{},"message":"Understood."}'
    registry = ActionRegistry(
        {"conversation": lambda intent: {"message": intent.message, "handled": True}},
        project_identifiers=("jazrielle", "business/portal"),
    )
    service = AssistantService(provider, "canonical prompt", action_registry=registry)

    await service.execute_command("open VS Code on jazrielle")

    assert "Configured project identifiers:" in provider.system
    assert "- jazrielle" in provider.system
    assert "- business/portal" in provider.system
```

Add an API capability assertion that the `start_project` examples include the discovered project identifier.

- [ ] **Step 2: Run the focused context tests and verify they fail**

```powershell
& $backendPython -m pytest -q tests/test_modules.py tests/test_api.py::test_capabilities_include_configured_project_examples
```

Expected: FAIL because the registry does not yet expose prompt context and the service sends only the file prompt.

- [ ] **Step 3: Implement the registry and service context**

Extend `ActionRegistry.__init__` with an optional `project_identifiers: Iterable[str] = ()`, retain a sorted tuple, and implement:

```python
def get_project_prompt_context(self) -> str:
    if not self._project_identifiers:
        return ""
    lines = "\n".join(f"- {identifier}" for identifier in self._project_identifiers)
    return f"Configured project identifiers:\n{lines}"
```

Pass `action_config.projects` keys from `build_action_registry`, and in `AssistantService` append the context only for `execute_command`:

```python
def _command_system_prompt(self) -> str:
    if self._action_registry is None:
        return self._system_prompt
    context = self._action_registry.get_project_prompt_context()
    return f"{self._system_prompt}\n\n{context}" if context else self._system_prompt
```

Use `_command_system_prompt()` for command generation. Keep open-ended inference on the canonical file prompt.

- [ ] **Step 4: Remove repository-specific names from the canonical prompt**

Replace the hardcoded repository list in rule 16 with an instruction to preserve an identifier from the generated configured-project context. Replace the Jazrielle-specific example with a generic configured project example using `project-name`.

- [ ] **Step 5: Run the context tests**

```powershell
& $backendPython -m pytest -q tests/test_modules.py tests/test_api.py::test_system_prompt_declares_target_and_url_safety_rules tests/test_api.py::test_capabilities_include_configured_project_examples
```

Expected: all focused context tests PASS.

- [ ] **Step 6: Commit dynamic model context**

```powershell
git add backend/app/modules/assistant/action_registry.py backend/app/modules/assistant/service.py ai/system-prompt.md backend/tests/test_api.py backend/tests/test_modules.py
git commit -m "feat: expose discovered projects to command model"
```

### Task 4: Update documentation and remove stale hardcoded claims

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`

- [ ] **Step 1: Update documentation text**

Document that project targets are discovered from Git repositories below `settings.projectRoot`, that excluded directories are skipped, that the VS Code command is fixed, and that adding a repository under the root makes it discoverable after backend restart. Remove lists of specific repository names.

- [ ] **Step 2: Check documentation formatting**

```powershell
git diff --check -- README.md backend/README.md
```

Expected: no whitespace errors.

- [ ] **Step 3: Commit documentation**

```powershell
git add README.md backend/README.md
git commit -m "docs: describe dynamic project discovery"
```

### Task 5: Run the complete verification suite

**Files:**
- Verify: all modified backend modules, tests, configuration, and documentation.

- [ ] **Step 1: Run the complete backend suite**

```powershell
cd backend
& $backendPython -m pytest -q
```

Expected: all tests PASS; existing Starlette and pytest cache warnings may remain.

- [ ] **Step 2: Run frontend typecheck and build**

```powershell
cd ..\frontend
npm.cmd run typecheck
npm.cmd run build
```

Expected: both commands exit successfully.

- [ ] **Step 3: Verify the final diff and commit status**

```powershell
cd ..
git diff --check
git status --short
git log -5 --oneline
```

Confirm the source changes contain no hardcoded repository list, no arbitrary shell execution, and no Tauri implementation.

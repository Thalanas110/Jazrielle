# Google Search Assistant Action Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Jazrielle interpret Google-search requests, fetch Google results in the backend, and return the useful result text without opening a browser.

**Architecture:** Add a server-side `SearchProvider` beside the existing weather network adapter. `GoogleSearchProvider` will request a fixed HTTPS Google search endpoint, parse only result titles, snippets, and standard HTTP(S) links, and return structured results. The registered `search_google` action will validate the query, call the provider, and format the results into `CommandResult.message` with no `launchUrl`.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, urllib, stdlib `html.parser`, pytest, Markdown system prompt.

## Global Constraints

- The model may supply only a search query; the backend owns the Google host, HTTPS scheme, request headers, timeout, and result parsing.
- Empty or whitespace-only queries must return `handled=False` without a network request.
- Search failures must return a user-facing unavailable message rather than raise a 422 or open a browser.
- Search responses must leave `CommandResult.launchUrl` as `None`.
- Preserve existing action behavior and generated/unrelated worktree files.

---

### Task 1: Add a failing provider and action regression test

**Files:**
- Modify: `backend/tests/test_url_git_actions.py`
- Modify: `backend/tests/test_command_integration.py`
- Modify: `backend/tests/test_api.py`
- Modify: `backend/tests/support.py`
- Create: `backend/tests/test_network_search.py`

**Interfaces:**
- The tests will require `SearchResult(title: str, url: str, snippet: str)`, a `SearchProvider.search(query: str) -> list[SearchResult]`, and a registered `search_google` action.

- [ ] **Step 1: Add the direct action and integration expectations.**

Add a fake search provider and tests asserting that a valid query is returned as text, no browser metadata is emitted, and an empty query is rejected.

```python
class FakeSearchProvider:
    def __init__(self, results):
        self.results = results
        self.query = None

    def search(self, query: str):
        self.query = query
        return self.results


def test_search_google_returns_results_without_a_launch_url():
    search = FakeSearchProvider([
        SearchResult("PAGASA", "https://pagasa.dost.gov.ph/", "Rainfall warning information."),
    ])
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main"), search=search),
    ).execute(intent("search_google", {"query": "color coded rainfall warning for Cebu"}))

    assert result.handled is True
    assert "PAGASA" in result.message
    assert result.launchUrl is None
    assert search.query == "color coded rainfall warning for Cebu"


def test_search_google_rejects_an_empty_query_without_searching():
    search = FakeSearchProvider([])
    result = build_action_registry(
        AssistantActionConfig(),
        SimpleNamespace(git=FakeGitAdapter("## main"), search=search),
    ).execute(intent("search_google", {"query": "  "}))

    assert result.handled is False
    assert search.query is None
```

- [ ] **Step 2: Add the API regression test for the former 422.**

Use `ConfiguredJsonProvider` with a `search_google` JSON response and a fake search adapter, then assert `POST /api/jarvis/execute` returns 200 and `launchUrl` is `None`.

```python
def test_google_search_command_returns_text_without_opening_a_browser():
    provider = ConfiguredJsonProvider(
        '{"action":"search_google","arguments":{"query":"rainfall warning for Cebu"},"message":"Searching Google."}'
    )
    search = FakeSearchProvider([
        SearchResult("PAGASA", "https://pagasa.dost.gov.ph/", "Rainfall warning information."),
    ])
    application = create_app(
        model_provider=provider,
        adapters=SimpleNamespace(search=search),
    )

    response = TestClient(application).post(
        "/api/jarvis/execute",
        json={"command": "check the color coded rainfall warning for Cebu province right now"},
    )

    assert response.status_code == 200
    assert response.json()["handled"] is True
    assert "PAGASA" in response.json()["message"]
    assert response.json()["launchUrl"] is None
```

- [ ] **Step 3: Add parser/provider contract tests.**

Cover standard Google result markup, `/url?q=` redirect links, and non-HTTP links being ignored. Patch the module’s `urlopen` with a context-managed fake response so the test uses the real parser and provider.

- [ ] **Step 4: Run the focused tests and verify they fail for the missing action/provider.**

Run: `python -m pytest backend/tests/test_url_git_actions.py backend/tests/test_command_integration.py backend/tests/test_network_search.py -q`

Expected: FAIL with import/validation failures because `SearchResult` and `search_google` do not exist yet.

### Task 2: Implement server-side Google result retrieval

**Files:**
- Modify: `backend/app/modules/assistant/adapters/network.py`

**Interfaces:**
- Produces `SearchResult`, `SearchProvider`, and `GoogleSearchProvider.search(query: str) -> list[SearchResult]` for the action registry.

- [ ] **Step 1: Implement the minimal Google result model and provider.**

Add a frozen `SearchResult` dataclass, a `SearchProvider` protocol, and `GoogleSearchProvider`. Request `https://www.google.com/search?` with `urlencode({"q": query, "num": 5, "hl": "en"})`, set `User-Agent: Jazrielle/1.0`, and use a five-second timeout. Parse HTML with `HTMLParser`, normalize `/url?q=` links with `parse_qs`, and keep only absolute `http`/`https` links without embedded credentials.

- [ ] **Step 2: Run the focused provider tests.**

Run: `python -m pytest backend/tests/test_network_search.py -q`

Expected: PASS.

- [ ] **Step 3: Commit the provider.**

```powershell
git add backend/app/modules/assistant/adapters/network.py backend/tests/test_network_search.py
git commit -m "feat: add server-side Google search provider"
```

### Task 3: Register the search action and eliminate the 422

**Files:**
- Modify: `backend/app/modules/assistant/intent.py`
- Modify: `backend/app/modules/assistant/action_registry.py`
- Modify: `backend/tests/test_url_git_actions.py`
- Modify: `backend/tests/test_command_integration.py`

**Interfaces:**
- Consumes `SearchProvider` and `SearchResult` from Task 2.
- Produces valid `AssistantIntent(action="search_google", arguments={"query": ...})` handling and a text-only `CommandResult`.

- [ ] **Step 1: Add `search_google` to the action literal and registry.**

Inject `GoogleSearchProvider` by default or `adapters.search` in tests. Validate a non-empty string query, call `search.search(query)`, catch `OSError`, `TimeoutError`, and `ValueError`, and format up to three result rows as `Title — snippet`. Return `handled=False` for unavailable search and `handled=True` for results or no-result responses. Do not set `launchUrl`.

- [ ] **Step 2: Run the focused tests and verify the former 422 is gone.**

Run: `python -m pytest backend/tests/test_url_git_actions.py backend/tests/test_command_integration.py -q`

Expected: PASS, including the API request with the rainfall-warning wording returning HTTP 200.

- [ ] **Step 3: Commit the action.**

```powershell
git add backend/app/modules/assistant/intent.py backend/app/modules/assistant/action_registry.py backend/tests/test_url_git_actions.py backend/tests/test_command_integration.py
git commit -m "feat: execute Google searches without browser launch"
```

### Task 4: Teach the model and document the capability

**Files:**
- Modify: `ai/system-prompt.md`
- Modify: `backend/tests/test_api.py`
- Modify: `README.md`

**Interfaces:**
- The prompt advertises the registered `search_google` action and maps current-information lookup requests to it.
- The capabilities endpoint exposes `search_google` to the frontend and model context.

- [ ] **Step 1: Update the canonical system prompt.**

Add `search_google` to the available actions and add rules/examples saying that requests to search, look up, check current conditions, or find online information use `search_google` with the user’s concise query; the backend returns the results and no browser is opened. Keep `open_url` for explicit URLs only.

- [ ] **Step 2: Update capability assertions and README behavior documentation.**

Include `search_google` in the expected action set and document that online lookups are fetched by the backend and returned in the response message; `launchUrl` stays null for searches.

- [ ] **Step 3: Run the complete verification suite.**

Run: `python -m pytest backend/tests -q`

Expected: all backend tests pass.

- [ ] **Step 4: Commit prompt and documentation updates.**

```powershell
git add ai/system-prompt.md backend/tests/test_api.py README.md
git commit -m "docs: expose Google search assistant action"
```

### Task 5: Final verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Run backend tests and frontend typecheck.**

Run: `python -m pytest backend/tests -q` and `npm.cmd run typecheck`.

- [ ] **Step 2: Inspect the final diff and status.**

Run: `git diff --check`, `git diff HEAD~4..HEAD --stat`, and `git status --short --branch`. Confirm only intended source, test, plan, prompt, and README changes are present; preserve generated pytest/build artifacts already present before this feature.

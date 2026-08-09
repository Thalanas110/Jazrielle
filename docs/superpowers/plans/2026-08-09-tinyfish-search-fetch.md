# TinyFish Search and Fetch Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fragile direct Google HTML scraper with a server-side TinyFish Search → Fetch pipeline that never uses TinyFish Agent or Browser APIs and never opens a local browser.

**Status:** Implemented and verified on `master`.

**Architecture:** Keep the existing `search_google` model action and `SearchResult` contract. Add separate `TinyFishSearchProvider` and `TinyFishFetchProvider` adapters that call only `api.search.tinyfish.ai` and `api.fetch.tinyfish.ai` with `X-API-Key`. The action searches for structured results, fetches the top HTTPS result pages with `ttl=0`, and returns fetched text with search snippets as a fallback.

**Tech Stack:** Python 3.11, FastAPI, Pydantic Settings, stdlib `urllib`, JSON, pytest, TinyFish Search API, TinyFish Fetch API.

## Global Constraints

- Do not call TinyFish Agent API, Browser API, or any local/browser-launch path for search.
- Do not scrape Google HTML directly.
- Read the TinyFish key from `TINYFISH_API_KEY`; never commit a key.
- Search defaults to Philippine English results (`PH`, `en`) and Fetch uses `ttl=0` for current pages.
- A successful search remains useful if individual page fetches fail; return search snippets instead.
- Missing configuration must say how to configure the key, not claim a generic transient outage.

---

### Task 1: Add failing Search and Fetch adapter tests

**Files:**
- Modify: `backend/tests/test_network_search.py`
- Modify: `backend/tests/test_url_git_actions.py`
- Modify: `backend/tests/test_command_integration.py`

**Interfaces:**
- Require `TinyFishSearchProvider`, `TinyFishFetchProvider`, `FetchedPage`, and `SearchNotConfiguredError`.
- Require `FetchProvider.fetch(urls: list[str], purpose: str) -> dict[str, FetchedPage]` and a search action that combines both providers.

- [ ] **Step 1: Replace the direct-Google parser test with TinyFish Search and Fetch HTTP contract tests.**

Fake `urlopen` and assert the Search request uses `https://api.search.tinyfish.ai`, `X-API-Key`, `location=PH`, `language=en`, and the user query. Assert the Fetch request uses `POST https://api.fetch.tinyfish.ai`, `ttl=0`, Markdown output, and the requested URLs. Add a missing-key test.

- [ ] **Step 2: Extend the action test with a fake fetch provider.**

Assert `search_google` calls search, fetches the returned URL, places fetched page text in `CommandResult.message`, and leaves `launchUrl` unset. Assert a fetch failure falls back to the search snippet.

- [ ] **Step 3: Keep the API regression test on the rainfall command.**

Inject fake search and fetch providers and assert the request returns 200 with fetched text and no browser metadata.

- [ ] **Step 4: Run the focused tests and verify they fail because TinyFish adapters do not exist.**

Run: `python -m pytest tests/test_network_search.py tests/test_url_git_actions.py tests/test_command_integration.py -q`

Expected: collection/import failures for the missing TinyFish interfaces.

### Task 2: Implement TinyFish Search and Fetch adapters

**Files:**
- Modify: `backend/app/modules/assistant/adapters/network.py`

**Interfaces:**
- Produces `TinyFishSearchProvider.search(query: str) -> list[SearchResult]`.
- Produces `TinyFishFetchProvider.fetch(urls: list[str], purpose: str) -> dict[str, FetchedPage]`.

- [ ] **Step 1: Implement typed result models and provider protocols.**

Add `FetchedPage`, `FetchProvider`, `SearchNotConfiguredError`, and constants for the two TinyFish endpoints. Retain `SearchResult` compatibility while deleting the Google HTML parser and direct Google URL construction.

- [ ] **Step 2: Implement Search API requests.**

Build a GET request with `query`, `purpose`, `location`, and `language`, send `X-API-Key`, decode JSON, and retain only result entries with safe absolute HTTP(S) URLs.

- [ ] **Step 3: Implement Fetch API requests.**

Build a POST request with at most three result URLs, `format: markdown`, `ttl: 0`, and a bounded `purpose`. Decode successful pages into `FetchedPage` values keyed by their requested URL; tolerate per-URL errors represented by TinyFish’s `errors` response field.

- [ ] **Step 4: Run adapter tests and commit.**

Run: `python -m pytest tests/test_network_search.py -q`

```powershell
git add backend/app/modules/assistant/adapters/network.py backend/tests/test_network_search.py
git commit -m "feat: use TinyFish search and fetch APIs"
```

### Task 3: Wire providers into the action and application settings

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/modules/assistant/action_registry.py`
- Modify: `backend/tests/test_url_git_actions.py`
- Modify: `backend/tests/test_command_integration.py`

**Interfaces:**
- `Settings.tinyfish_api_key: str | None` reads `TINYFISH_API_KEY` from `.env`.
- `build_action_registry(..., tinyfish_api_key=...)` creates TinyFish defaults while preserving adapter injection in tests.

- [ ] **Step 1: Add settings plumbing without adding a secret.**

Add an optional `tinyfish_api_key` setting and pass it from `create_app` into the action registry. Default location and language are `PH` and `en`; they may be overridden by `TINYFISH_LOCATION` and `TINYFISH_LANGUAGE` settings.

- [ ] **Step 2: Combine search and fetch in `search_google`.**

Call Search first, Fetch the top three URLs second, and format fetched text when available. Catch configuration errors with `Web search is not configured. Add TINYFISH_API_KEY to backend/.env.`; catch transport errors with a clear unavailable message; use snippets if Fetch fails. Always return `launchUrl=None`.

- [ ] **Step 3: Run the focused API tests and commit.**

Run: `python -m pytest tests/test_url_git_actions.py tests/test_command_integration.py -q`

```powershell
git add backend/app/core/config.py backend/app/main.py backend/app/modules/assistant/action_registry.py backend/tests/test_url_git_actions.py backend/tests/test_command_integration.py
git commit -m "feat: wire TinyFish content into search action"
```

### Task 4: Document strict API scope and setup

**Files:**
- Modify: `backend/tests/test_api.py`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `ai/system-prompt.md`

**Interfaces:**
- Documentation names only TinyFish Search and Fetch as the online lookup integrations.
- No Agent or Browser API appears in the runtime path or setup instructions.

- [ ] **Step 1: Update prompt and capability assertions.**

Keep the `search_google` action name but state that the backend uses server-side Search and Fetch and does not open a browser.

- [ ] **Step 2: Document `TINYFISH_API_KEY`, Philippine search defaults, and fresh Fetch behavior.**

Tell developers to place the key only in `backend/.env`, restart the backend after changing it, and never commit it.

- [ ] **Step 3: Run full verification and commit documentation.**

Run: `python -m pytest tests -q` and `npm.cmd run typecheck`.

```powershell
git add ai/system-prompt.md README.md backend/README.md backend/tests/test_api.py docs/superpowers/plans/2026-08-09-tinyfish-search-fetch.md
git commit -m "docs: configure TinyFish search and fetch"
```

### Task 5: Final verification

**Files:**
- No source changes expected.

- [ ] **Step 1: Verify committed changes.**

Run: `git diff --check HEAD~3..HEAD` and inspect `git status --short --branch`. Confirm no `.env` secret was staged and no Agent/Browser endpoint appears in changed runtime files.

- [ ] **Step 2: Re-run the complete backend and frontend checks.**

Run: `python -m pytest tests -q` and `npm.cmd run typecheck`.

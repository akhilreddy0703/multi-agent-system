# Testing

Automated and manual testing for the Multi-Agent RAG system.

## E2E tests

Full end-to-end run (auth, AgentOS, weather, Todo MCP, chat, streaming). Requires **backend** and **Todo MCP** (and Milvus) running.

```bash
# Start backend + Todo MCP (and Milvus) first, then:
uv run python tests/e2e_test.py
```

All steps should **PASS**. Covers: login, login page, teams/config, team run, weather, Todo MCP, `/chat` and `/chat/stream`, FAQ delegation, streaming showcase, edge cases.

## Unit and integration tests

```bash
uv run pytest tests/ -v
```

Use for fast feedback; some tests may require mocks or skip without live Milvus/MCP.

## Manual testing

- **API (curl):** [MANUAL_API_TEST.md](MANUAL_API_TEST.md) — step-by-step for `/auth/login`, `/teams`, `/chat`, `/chat/stream`, `/weather`, `/todos`.
- **UI (agent-ui):** [UI_SETUP.md](UI_SETUP.md) — connect agent-ui to the backend, sign in, and test FAQ, weather, and Todo in the chat.

## Test layout

| Path | Purpose |
|------|---------|
| `tests/e2e_test.py` | Full E2E script |
| `tests/test_auth.py` | Auth routes |
| `tests/test_chat.py` | Chat endpoints |
| `tests/test_todo.py` | Todo proxy |
| `tests/test_weather.py` | Weather endpoint |
| `tests/conftest.py` | Pytest fixtures |

# Code Review

Reviewed: all source files in `backend/`, `frontend/src/`, `Dockerfile`, `scripts/`, and configuration files.
All 34 tests pass (19 backend, 9 frontend unit, 6 e2e) at time of review.

---

## Issues by priority

### High

**1. `backend/data/` not in `.gitignore`**
The SQLite database defaults to `backend/data/app.db`. That path is not excluded in `.gitignore`. If the app is run locally outside Docker, the database file can be committed accidentally. `.gitignore` excludes `db.sqlite3` (Django convention) but not `.db` files generally.

Action: add `backend/data/` to `.gitignore`.

---

**2. Synchronous HTTP client blocks the FastAPI event loop**
`backend/app/ai.py` uses `httpx.post(...)` (synchronous). FastAPI is async-first; a blocking network call on the AI request will stall the entire event loop for its duration (up to 30 s timeout). For a single-user local MVP this is harmless, but it is a correctness issue if concurrency ever matters.

Action: replace with `httpx.AsyncClient` and `await` in an `async def request_ai_message`.

---

### Medium

**3. Duplicate `_login` helper across three test files**
`test_auth.py`, `test_board_api.py`, and `test_ai_board_updates.py` each define an identical `_login(client)` function. Any change to the login flow requires updating three places.

Action: extract to a shared `conftest.py` fixture in `backend/tests/`.

---

**4. `DEFAULT_BOARD` (Python) and `initialData` (TypeScript) are identical and unsynchronised**
`backend/app/db.py:37` and `frontend/src/lib/kanban.ts:18` contain the same seed board data. The frontend copy is only used when `disablePersistence=true` (tests and preview). If the seed data changes in one place it silently diverges in the other.

Action: either accept the duplication and add a comment noting they must stay in sync, or remove `initialData` from `kanban.ts` entirely and only use it in tests via the `initialBoard` prop backed by a fixture.

---

**5. Chat message `key` uses array index**
In `KanbanBoard.tsx:422`:
```tsx
key={`${message.role}-${index}`}
```
Using index as key causes React to mis-reconcile messages when items are prepended or the list is otherwise mutated. Messages should have a stable unique ID.

Action: add an `id` field to `ChatMessage` (e.g. `crypto.randomUUID()`) and use it as the key.

---

**6. `snapshot_json` is written but never read in the API path**
`db.py:_write_board` computes and stores `snapshot_json` on every write. `_read_board` (the only function called by the API) always reads from the normalised tables and ignores the snapshot. `get_raw_snapshot()` exists but is only called in tests. The snapshot write is dead code in the production read path.

Action: either use the snapshot in `_read_board` to avoid the join (as originally intended), or remove it entirely to simplify the write path and schema. Leaving it as-is creates a false impression that reads use it.

---

**7. `handleAddCard` hardcodes a display string as a data value**
In `KanbanBoard.tsx:201`:
```ts
details: details || "No details yet."
```
Cards created via the UI with an empty details field are stored as the string `"No details yet."`. Cards created by the AI without a details field are stored as `""` (the DB column default). This inconsistency surfaces as a visible difference when both types of cards appear on the board.

Action: remove the fallback; store `""` and handle the empty state in the display layer (`KanbanCard.tsx`) if needed.

---

**8. `createId` uses `Math.random()`**
`kanban.ts:164` generates card IDs using `Math.random()`. The random part is only 6 base-36 characters (~2.2 billion combinations). Collision is unlikely in practice but `crypto.randomUUID()` is available in all target environments and is the idiomatic approach.

Action: replace with `crypto.randomUUID()` or `\`card-${crypto.randomUUID()}\``.

---

### Low

**9. Conversation history sent as a stringified blob rather than structured messages**
`ai_board.py:build_ai_board_prompt` embeds the full conversation history as a JSON string inside a single user message. OpenRouter supports the standard OpenAI chat format (alternating `user`/`assistant` roles in the `messages` array). Sending history as structured turns is more effective for the model's context window and reduces prompt engineering friction.

Action: build the `messages` list as a proper alternating `user`/`assistant` sequence with a system message, passing history as separate entries rather than as a JSON blob in the user turn.

---

**10. No cap on conversation history size**
`KanbanBoard.tsx` accumulates messages in state indefinitely and sends the full history on every chat request. A long session will produce very large prompts. There is no truncation or limit.

Action: cap history at a fixed number of turns (e.g. last 10 messages) before sending to the backend.

---

**11. `SESSION_SECRET` fallback means users are logged out on every restart**
When `SESSION_SECRET` is not set, a random secret is generated at startup (`main.py:26`). All sessions are invalidated on each container restart. This is noted behaviour for the MVP but there is no documentation warning that `SESSION_SECRET` should be in `.env` for persistence. The current `.env` file does not include it.

Action: document `SESSION_SECRET` in the project README or AGENTS.md and consider adding it to `.env` with a generated value.

---

**12. No test for card content editing**
Cards can be created and deleted, and these are tested. However editing a card's title or details (the most common Kanban interaction) has no dedicated test in either unit or e2e suites. It is implicitly exercised by the AI board update tests but not as a first-class user action.

Action: add a unit test for editing a card title/details through the `applyBoardUpdate` path, and/or an e2e test for inline card editing once that feature is added to the UI.

---

**13. E2E tests mock all backend APIs**
`tests/kanban.spec.ts` uses Playwright route interception to mock every API call. This is fast and reliable but means no end-to-end test ever hits the real FastAPI backend. Integration regressions between the frontend payload shape and the backend Pydantic models would not be caught.

Action: consider adding a single smoke e2e test that runs against the Docker container (`PLAYWRIGHT_BASE_URL` pointing at a live container) as an opt-in CI step, similar to the backend's `@pytest.mark.integration` pattern.

---

**14. Dockerfile frontend builder uses Node 22, local dev requires Node 24**
The `Dockerfile` uses `node:22-bookworm-slim` for the frontend build stage. The `npm run build` step (Next.js static export) does not use jsdom so this works. However, local test runs fail on Node 18 and require Node 24 due to jsdom@27. This discrepancy is not documented and can cause confusion.

Action: pin Node version in `package.json` `engines` field, or document the Node 24 requirement explicitly in CLAUDE.md (already partially done).

---

## Summary table

| # | Area | Severity | Action |
|---|------|----------|--------|
| 1 | `.gitignore` | High | Add `backend/data/` |
| 2 | `ai.py` | High | Use async httpx |
| 3 | Tests | Medium | Shared `conftest.py` login fixture |
| 4 | Data duplication | Medium | Acknowledge or remove `initialData` |
| 5 | `KanbanBoard.tsx` | Medium | Stable chat message keys |
| 6 | `db.py` snapshot | Medium | Use or remove snapshot read path |
| 7 | `KanbanBoard.tsx` | Medium | Remove "No details yet." fallback |
| 8 | `kanban.ts` | Medium | Use `crypto.randomUUID()` |
| 9 | `ai_board.py` | Low | Structured chat message turns |
| 10 | `KanbanBoard.tsx` | Low | Cap history length |
| 11 | `main.py` | Low | Document `SESSION_SECRET` |
| 12 | Tests | Low | Test card edit flow |
| 13 | Tests | Low | Real-backend e2e smoke test |
| 14 | Dockerfile | Low | Document Node version requirement |

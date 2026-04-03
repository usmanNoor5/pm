# Project Execution Plan

Execution rules:
- Follow Parts 1 through 10 in sequence.
- Low-risk tasks can be batched inside a part.
- Pause for user approval at the checkpoints marked below.
- Keep implementation simple and MVP-focused.

## Locked Design Decisions

- Runtime architecture:
	- Single Docker container for MVP.
	- FastAPI serves statically exported frontend at `/`.
- Python packaging/runtime:
	- `uv` is used for dependency/install/run workflows in container.
	- Container startup uses `python -m uvicorn` to avoid executable lookup issues.
- Session auth (MVP):
	- Hardcoded credentials (`user` / `password`).
	- Server-side in-memory sessions with signed HTTP-only cookie (`pm_session`).
	- Local secret key via env (`SESSION_SECRET`) with generated fallback.
- Data persistence:
	- SQLite database with normalized tables (users, boards, columns, cards).
	- Optional board JSON snapshot stored per board for fast full-board reads.
	- DB auto-creation/bootstrap at startup, with default seeded board data.
- Frontend-backend sync:
	- Frontend board state source is backend APIs (`GET /api/board`, `PUT /api/board`).
	- Save-flow guards against stale async responses overwriting newer edits.
- Local script behavior:
	- Start scripts support `HOST_PORT` override to avoid local port conflicts.
	- Start scripts mount a persistent Docker volume for SQLite data so board changes survive container recreation.

## Part 1: Planning and Baseline Documentation

Status checklist:
- [x] Rewrite this plan with detailed substeps, tests, and success criteria.
- [x] Document current frontend architecture in `frontend/AGENTS.md`.
- [x] Confirm implementation choices captured from user:
	- [x] Single Docker container for MVP (FastAPI + built frontend)
	- [x] Server-side cookie session auth only (local signing secret)
	- [x] Normalized DB schema + optional JSON snapshot
	- [x] Strict AI output schema + controlled fallback path
- [x] Get user sign-off before moving to Part 2.

Tests:
- Manual review of plan completeness and consistency with root `AGENTS.md`.

Success criteria:
- Every part includes concrete tasks, test strategy, and acceptance criteria.
- `frontend/AGENTS.md` accurately describes existing frontend code.
- User explicitly approves the plan.

Checkpoint:
- Required approval before Part 2.

## Part 2: Scaffolding (Docker + FastAPI + Scripts)

Status checklist:
- [x] Create backend FastAPI app skeleton in `backend/`.
- [x] Add Docker build/runtime configuration for single-container MVP.
- [x] Use `uv` for Python dependency management inside container.
- [x] Add start/stop scripts for Linux, macOS, and Windows in `scripts/`.
- [x] Add a minimal `GET /api/health` endpoint.
- [x] Serve simple static hello-world page from FastAPI first.

Tests:
- Container build succeeds locally.
- App starts from scripts on Linux/macOS/Windows command variants.
- `GET /` returns hello-world HTML.
- `GET /api/health` returns success JSON.
- General persistence validation: make a data change, restart with the normal start/stop scripts, and confirm the change is still present.

Success criteria:
- One command path to build and run locally is documented and works.
- Backend is reachable on configured port.
- Static + API route confirmed end-to-end.
- Local restarts do not reset persisted board data.

## Part 3: Add Existing Frontend Build and Serving

Status checklist:
- [x] Configure frontend build output for static serving.
- [x] Integrate built frontend assets into FastAPI serving at `/`.
- [x] Preserve current Kanban UI behavior from `frontend/` demo.
- [x] Update scripts/container flow to include frontend build step.

Tests:
- Frontend unit tests pass (`vitest`).
- Frontend e2e tests pass (`playwright`) against served app.
- `GET /` loads Kanban board with expected columns/cards.

Success criteria:
- App root shows demo Kanban from built frontend, not placeholder HTML.
- Drag/drop and card add/delete still work in served build.

## Part 4: Fake User Sign-In (MVP Auth)

Status checklist:
- [x] Add backend login route validating hardcoded credentials (`user` / `password`).
- [x] Implement secure server-side session cookie handling.
- [x] Generate/load local session signing secret from environment.
- [x] Add logout route to clear session.
- [x] Gate Kanban access behind authenticated session.
- [x] Add simple login UI/flow in frontend.

Tests:
- Backend auth tests: successful login, failed login, logout, unauthorized access.
- Frontend tests: login form behavior, redirect/gating, logout flow.
- E2E test: unauthenticated user sees login, authenticated user sees Kanban.

Success criteria:
- Only valid credentials grant access.
- Session persists across page reload.
- Logout reliably clears access.

## Part 5: Database Modeling and Design Sign-Off

Status checklist:
- [x] Propose normalized schema for users, boards, columns, cards.
- [x] Add optional board snapshot JSON strategy and rationale.
- [x] Define migration/bootstrap strategy for creating DB if missing.
- [x] Document schema and tradeoffs in `docs/`.
- [x] Get user sign-off before implementing persistence APIs.

Tests:
- Design review only (no production persistence behavior yet).

Success criteria:
- Schema supports current MVP and future multi-user growth.
- Documentation is clear on reads/writes and snapshot usage.

Checkpoint:
- Required approval before Part 6.

## Part 6: Backend Persistence API

Status checklist:
- [x] Implement SQLite setup and auto-create logic at startup.
- [x] Implement data access layer for board read/write operations.
- [x] Add API routes for board fetch/update per authenticated user.
- [x] Validate request payloads and enforce consistent response models.

Tests:
- Backend unit tests for CRUD/data mapping behavior.
- API tests for authorized and unauthorized cases.
- Startup test verifies DB file/table creation when absent.
- General persistence regression check: verify representative CRUD changes remain after service restart.

Success criteria:
- Board state persists between restarts.
- API contract is stable and validated.

## Part 7: Frontend + Backend Integration

Status checklist:
- [x] Replace frontend in-memory board source with backend API.
- [x] Load board on app startup after login.
- [x] Persist column rename/card create/move/edit/delete through API.
- [x] Handle loading and error states minimally but clearly.

Tests:
- Frontend integration tests with API mocking.
- E2E tests verifying persistence across page reload.
- Regression tests for drag/drop + edit flows.

Success criteria:
- UI actions update backend and survive refresh.
- No local-only state divergence from persisted board.

## Part 8: AI Connectivity via OpenRouter

Status checklist:
- [x] Add backend OpenRouter client configuration.
- [x] Use `OPENROUTER_API_KEY` from project `.env`.
- [x] Configure model `qwen/qwen3.6-plus:free`.
- [x] Add minimal connectivity route/service for AI test prompt.

Tests:
- Integration test path for a simple `2+2` prompt (can be opt-in/manual if key unavailable in CI).
- Error handling tests for missing API key and HTTP failures.

Success criteria:
- Backend can complete a basic AI request and return parsed response.
- Failures return controlled, non-crashing errors.

## Part 9: Structured AI Board Updates

Status checklist:
- [x] Define strict JSON schema for AI response payload.
- [x] Send current Kanban JSON + user message + conversation history to AI.
- [x] Parse/validate structured output in backend.
- [x] Apply optional board update transactionally when valid.
- [x] Add controlled fallback when model output is malformed.

Tests:
- Unit tests for schema validation and parser.
- Integration tests for:
	- [x] Response-only (no board update)
	- [x] Valid board update
	- [x] Invalid/malformed AI payload fallback

Success criteria:
- AI contract is deterministic at backend boundary.
- Invalid AI output never corrupts persisted board state.

## Part 10: Frontend AI Assistant UI and Live Refresh

Status checklist:
- [x] Build compact floating chat UI integrated into Kanban experience.
- [x] Render conversation history and message states.
- [x] Call backend AI endpoint from frontend.
- [x] Update board UI automatically when AI response includes board changes.
- [x] Keep styling aligned with project color scheme and current visual language.

Tests:
- Component tests for chat interactions and render states.
- Integration tests for AI response handling and board refresh behavior.
- E2E happy-path test for user message causing board update.

Success criteria:
- Chat is functional and visually integrated.
- AI-driven board updates appear without manual refresh.
- Existing Kanban interactions continue to work.

## Global Definition of Done

Status checklist:
- [ ] All required tests pass for each completed part.
- [ ] Documentation remains concise and current.
- [ ] No extra non-MVP features are introduced.
- [ ] Root-cause-driven fixes used when issues arise.
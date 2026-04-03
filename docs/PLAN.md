# Project Execution Plan

Execution rules:
- Follow Parts 1 through 10 in sequence.
- Low-risk tasks can be batched inside a part.
- Pause for user approval at the checkpoints marked below.
- Keep implementation simple and MVP-focused.

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

Success criteria:
- One command path to build and run locally is documented and works.
- Backend is reachable on configured port.
- Static + API route confirmed end-to-end.

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
- [ ] Add backend OpenRouter client configuration.
- [ ] Use `OPENROUTER_API_KEY` from project `.env`.
- [ ] Configure model `qwen/qwen3.6-plus-preview:free`.
- [ ] Add minimal connectivity route/service for AI test prompt.

Tests:
- Integration test path for a simple `2+2` prompt (can be opt-in/manual if key unavailable in CI).
- Error handling tests for missing API key and HTTP failures.

Success criteria:
- Backend can complete a basic AI request and return parsed response.
- Failures return controlled, non-crashing errors.

## Part 9: Structured AI Board Updates

Status checklist:
- [ ] Define strict JSON schema for AI response payload.
- [ ] Send current Kanban JSON + user message + conversation history to AI.
- [ ] Parse/validate structured output in backend.
- [ ] Apply optional board update transactionally when valid.
- [ ] Add controlled fallback when model output is malformed.

Tests:
- Unit tests for schema validation and parser.
- Integration tests for:
	- [ ] Response-only (no board update)
	- [ ] Valid board update
	- [ ] Invalid/malformed AI payload fallback

Success criteria:
- AI contract is deterministic at backend boundary.
- Invalid AI output never corrupts persisted board state.

## Part 10: Frontend AI Sidebar and Live Refresh

Status checklist:
- [ ] Build sidebar chat UI integrated into Kanban layout.
- [ ] Render conversation history and message states.
- [ ] Call backend AI endpoint from frontend.
- [ ] Update board UI automatically when AI response includes board changes.
- [ ] Keep styling aligned with project color scheme and current visual language.

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
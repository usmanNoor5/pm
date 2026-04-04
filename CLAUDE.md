# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Kanban-based Project Management MVP with an AI assistant. Single Docker container ships a FastAPI backend (Python) that serves a statically-exported Next.js frontend at `/`.

## Commands

### Backend (run from `backend/`)

```bash
# Run all backend tests
# Note: -p flags suppress ROS pytest plugins that exist in this environment
cd backend && python -m pytest tests/ -p no:launch_testing -p no:launch_ros

# Run a single test file
cd backend && python -m pytest tests/test_auth.py -p no:launch_testing -p no:launch_ros

# Run integration tests (requires OPENROUTER_API_KEY)
cd backend && python -m pytest tests/ -m integration -p no:launch_testing -p no:launch_ros

# Run backend dev server directly (no Docker)
cd backend && python -m uvicorn app.main:app --reload --port 8000
```

### Frontend (run from `frontend/`)

> **Node version:** jsdom@27 (pulled in by vitest@3) requires Node 20+. Use `nvm use 24` before running frontend tests/dev.


```bash
# Unit tests (vitest)
cd frontend && npm run test:unit

# Watch mode
cd frontend && npm run test:unit:watch

# E2E tests (playwright, starts dev server automatically)
cd frontend && npm run test:e2e

# Run all tests
cd frontend && npm run test:all

# Build static export
cd frontend && npm run build

# Lint
cd frontend && npm run lint
```

### Docker (run from project root)

```bash
# Start (Linux)
./scripts/start-linux.sh

# Stop (Linux)
./scripts/stop-linux.sh

# Override port
HOST_PORT=9000 ./scripts/start-linux.sh
```

A `.env` file in the project root must contain `OPENROUTER_API_KEY`.

## Architecture

### Runtime

FastAPI serves the statically exported Next.js build from `frontend-out/` at `/`. All API routes are under `/api/`. If `frontend-out/` is missing, FastAPI shows a placeholder HTML page.

### Backend (`backend/app/`)

- `main.py` — FastAPI app, all route handlers, session cookie auth (HMAC-signed, in-memory `_sessions` dict), Pydantic request/response models
- `db.py` — SQLite setup, schema bootstrap, board read/write (`get_board_for_user`, `replace_board_for_user`)
- `ai.py` — OpenRouter HTTP client (`request_ai_message`), model configured via `OPENROUTER_MODEL` env var (default: `qwen/qwen3.6-plus:free`)
- `ai_board.py` — Builds structured AI prompt with current board JSON + conversation history; parses and validates AI JSON response (`parse_ai_structured_output`)

Backend tests live in `backend/tests/` (not under `app/`).

### Frontend (`frontend/src/`)

- `app/page.tsx` → renders `<AuthApp />`
- `components/AuthApp.tsx` — top-level auth gate: checks `/api/auth/me`, shows login form or `<KanbanBoard />`
- `components/KanbanBoard.tsx` — main board UI; fetches from `/api/board`, persists changes to `/api/board` (PUT), includes the floating AI assistant panel
- `components/KanbanColumn.tsx`, `KanbanCard.tsx`, `KanbanCardPreview.tsx`, `NewCardForm.tsx` — Kanban UI primitives using `@dnd-kit`
- `lib/kanban.ts` — Pure board state logic (add/move/edit/delete cards, rename columns)

Unit tests (`vitest` + jsdom + Testing Library) live in `src/` alongside their components. E2E tests (`playwright`) live in `frontend/tests/`.

### Data Flow

1. Login → `POST /api/auth/login` → HMAC-signed session cookie
2. Board load → `GET /api/board` → SQLite read via `db.py`
3. Any mutation → `PUT /api/board` with full board JSON → SQLite replace
4. AI chat → `POST /api/ai/chat` → builds structured prompt → OpenRouter → parse JSON response → optionally `replace_board_for_user` → returns updated board to frontend

### Auth

MVP hardcoded credentials: `user` / `password`. Sessions are in-memory (lost on restart). Cookie name: `pm_session`. Secret loaded from `SESSION_SECRET` env var; falls back to a randomly generated value on each start.

### Database

SQLite file auto-created at startup by `init_db()`. Tables: `users`, `boards`, `columns`, `cards`. The start scripts mount a Docker volume so the DB persists across container restarts.

## Color Scheme

- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991`
- Dark Navy: `#032147`
- Gray Text: `#888888`

## Coding Standards

- No over-engineering; keep it simple and MVP-focused
- No emojis anywhere
- Root-cause analysis before fixing bugs — prove with evidence
- No unnecessary defensive programming or extra features

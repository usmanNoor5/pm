# Backend Agent Guide

## Current scope

This backend currently provides Parts 3 through 9:
- FastAPI app bootstrapped in `backend/app/main.py`
- `GET /api/health` returns `{ "status": "ok" }`
- `GET /` serves statically exported frontend files from `/app/frontend-out` when present
- Fallback hello-world HTML is served at `/` if frontend export is unavailable
- Auth API (Part 4):
	- `GET /api/auth/me`
	- `POST /api/auth/login` (hardcoded `user` / `password`)
	- `POST /api/auth/logout`
- Session model:
	- Server-side in-memory session store
	- Signed HTTP-only cookie (`pm_session`) with local secret key
- Board API (Part 6):
	- `GET /api/board` (auth required)
	- `PUT /api/board` (auth required)
- AI API (Parts 8-9):
	- `POST /api/ai/ping` for minimal connectivity checks
	- `POST /api/ai/chat` for structured AI responses and optional board updates
- Persistence:
	- SQLite DB auto-created on startup (`backend/data/app.db` by default)
	- Normalized tables for users, boards, columns, cards
	- Optional snapshot JSON stored on `boards.snapshot_json`
	- Data persists across container recreation via mounted Docker volume (`/app/backend/data`)

## Runtime and packaging

- Python project metadata in `backend/pyproject.toml`
- Dependencies resolved in container with `uv sync`
- App runs via `uv run ... python -m uvicorn app.main:app`

## Notes for next phases

- OpenRouter model target: `qwen/qwen3.6-plus:free`.
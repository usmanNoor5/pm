# Backend Agent Guide

## Current scope

This backend currently provides the Part 3 scaffold:
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

## Runtime and packaging

- Python project metadata in `backend/pyproject.toml`
- Dependencies resolved in container with `uv sync`
- App runs via `uv run ... uvicorn app.main:app`

## Notes for next phases

- Add SQLite data layer and board APIs in Parts 5-7.
import hashlib
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from app.ai import AiServiceError, MissingApiKeyError, request_ai_message
from app.ai_board import build_ai_board_prompt, parse_ai_structured_output
from app.db import BoardModel, get_board_for_user, init_db, replace_board_for_user

SESSION_COOKIE_NAME = "pm_session"
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {
    "1",
    "true",
    "yes",
}
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32)

_sessions: dict[str, dict[str, str | float]] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Project Management MVP API", lifespan=lifespan)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthState(BaseModel):
    authenticated: bool
    username: str | None = None


class BoardResponse(BaseModel):
    board: BoardModel


class BoardUpdateRequest(BaseModel):
    board: BoardModel


class AiPingRequest(BaseModel):
    question: str = "2+2"


class AiChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[AiChatHistoryMessage] = Field(default_factory=list)


class AiServiceResponse(BaseModel):
    ok: bool
    model: str | None = None
    response: str | None = None
    error: str | None = None


class AiChatResponse(AiServiceResponse):
    board: BoardModel | None = None
    boardUpdated: bool = False
    fallbackUsed: bool = False


def _sign_session_id(session_id: str) -> str:
    digest = hmac.new(
        SESSION_SECRET.encode("utf-8"),
        session_id.encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()


def _encode_session_cookie(session_id: str) -> str:
    return f"{session_id}.{_sign_session_id(session_id)}"


def _decode_session_cookie(raw_cookie: str | None) -> str | None:
    if not raw_cookie or "." not in raw_cookie:
        return None
    session_id, signature = raw_cookie.rsplit(".", 1)
    expected_signature = _sign_session_id(session_id)
    if not hmac.compare_digest(signature, expected_signature):
        return None
    return session_id


def _cleanup_expired_sessions() -> None:
    now = time.time()
    expired_ids = [
        session_id
        for session_id, session in _sessions.items()
        if float(session["expires_at"]) <= now
    ]
    for session_id in expired_ids:
        _sessions.pop(session_id, None)


def _set_session_cookie(response: JSONResponse, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=_encode_session_cookie(session_id),
        max_age=SESSION_TTL_SECONDS,
        expires=SESSION_TTL_SECONDS,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )


def _current_username(request: Request) -> str | None:
    _cleanup_expired_sessions()
    session_id = _decode_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))
    if not session_id:
        return None

    session = _sessions.get(session_id)
    if not session:
        return None

    if float(session["expires_at"]) <= time.time():
        _sessions.pop(session_id, None)
        return None

    return str(session["username"])


def _require_user(request: Request) -> str:
    username = _current_username(request)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/me", response_model=AuthState)
def auth_me(request: Request) -> AuthState:
    username = _current_username(request)
    if not username:
        return AuthState(authenticated=False)
    return AuthState(authenticated=True, username=username)


@app.post("/api/auth/login", response_model=AuthState)
def auth_login(payload: LoginRequest) -> JSONResponse:
    if payload.username != "user" or payload.password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = {
        "username": payload.username,
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }

    response = JSONResponse(
        status_code=200,
        content=AuthState(authenticated=True, username=payload.username).model_dump(),
    )
    _set_session_cookie(response, session_id)
    return response


@app.post("/api/auth/logout", response_model=AuthState)
def auth_logout(request: Request) -> JSONResponse:
    session_id = _decode_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))
    if session_id:
        _sessions.pop(session_id, None)

    response = JSONResponse(
        status_code=200,
        content=AuthState(authenticated=False).model_dump(),
    )
    _clear_session_cookie(response)
    return response


@app.get("/api/board", response_model=BoardResponse)
def get_board(request: Request) -> BoardResponse:
    username = _require_user(request)
    return BoardResponse(board=get_board_for_user(username))


@app.put("/api/board", response_model=BoardResponse)
def update_board(payload: BoardUpdateRequest, request: Request) -> BoardResponse:
    username = _require_user(request)
    updated = replace_board_for_user(username, payload.board)
    return BoardResponse(board=updated)


@app.post("/api/ai/ping", response_model=AiServiceResponse)
async def ai_ping(payload: AiPingRequest, request: Request) -> JSONResponse:
    _require_user(request)

    try:
        reply = await request_ai_message(payload.question)
    except MissingApiKeyError as exc:
        return JSONResponse(
            status_code=503,
            content=AiServiceResponse(
                ok=False,
                model=os.getenv("OPENROUTER_MODEL"),
                response=None,
                error=str(exc),
            ).model_dump(),
        )
    except AiServiceError as exc:
        return JSONResponse(
            status_code=502,
            content=AiServiceResponse(
                ok=False,
                model=os.getenv("OPENROUTER_MODEL"),
                response=None,
                error=str(exc),
            ).model_dump(),
        )

    return JSONResponse(
        status_code=200,
        content=AiServiceResponse(
            ok=reply.ok,
            model=reply.model,
            response=reply.response,
            error=reply.error,
        ).model_dump(),
    )


@app.post("/api/ai/chat", response_model=AiChatResponse)
async def ai_chat(payload: AiChatRequest, request: Request) -> JSONResponse:
    username = _require_user(request)

    current_board = get_board_for_user(username)
    prompt = build_ai_board_prompt(
        user_message=payload.message,
        conversation_history=[m.model_dump() for m in payload.history],
        current_board=current_board,
    )

    try:
        reply = await request_ai_message(prompt)
    except MissingApiKeyError as exc:
        return JSONResponse(
            status_code=503,
            content=AiChatResponse(
                ok=False,
                model=os.getenv("OPENROUTER_MODEL"),
                response=None,
                error=str(exc),
                board=None,
                boardUpdated=False,
                fallbackUsed=False,
            ).model_dump(),
        )
    except AiServiceError as exc:
        return JSONResponse(
            status_code=502,
            content=AiChatResponse(
                ok=False,
                model=os.getenv("OPENROUTER_MODEL"),
                response=None,
                error=str(exc),
                board=None,
                boardUpdated=False,
                fallbackUsed=False,
            ).model_dump(),
        )

    parsed_response, parsed_board, fallback_used, parse_error = parse_ai_structured_output(
        reply.response or ""
    )

    applied_board: BoardModel | None = None
    board_updated = False
    if parsed_board is not None and not fallback_used:
        applied_board = replace_board_for_user(username, parsed_board)
        board_updated = True

    return JSONResponse(
        status_code=200,
        content=AiChatResponse(
            ok=True,
            model=reply.model,
            response=parsed_response,
            error=parse_error,
            board=applied_board,
            boardUpdated=board_updated,
            fallbackUsed=fallback_used,
        ).model_dump(),
    )


frontend_dir = Path(__file__).resolve().parents[2] / "frontend-out"

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return """
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>PM MVP - Hello</title>
    <style>
      body {
        font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #f7f8fb;
        color: #032147;
      }
      main {
        border: 1px solid rgba(3, 33, 71, 0.12);
        border-radius: 14px;
        padding: 24px 28px;
        background: #ffffff;
      }
      h1 {
        margin: 0 0 8px;
        font-size: 1.35rem;
      }
      p {
        margin: 0;
        color: #555;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Hello from FastAPI in Docker</h1>
      <p>Try <code>/api/health</code> for an API response.</p>
    </main>
  </body>
</html>
"""
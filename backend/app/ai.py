import os
import time
from dataclasses import dataclass
from logging import getLogger

import httpx

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.6-plus:free"
logger = getLogger(__name__)


class MissingApiKeyError(Exception):
    pass


class AiServiceError(Exception):
    pass


@dataclass
class AiReply:
    ok: bool
    model: str
    response: str | None
    error: str | None


def request_ai_message(prompt: str) -> AiReply:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise MissingApiKeyError("OPENROUTER_API_KEY is not configured")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
    started_at = time.perf_counter()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    referer = os.getenv("OPENROUTER_HTTP_REFERER")
    if referer:
        headers["HTTP-Referer"] = referer

    title = os.getenv("OPENROUTER_APP_TITLE")
    if title:
        headers["X-Title"] = title

    try:
        response = httpx.post(OPENROUTER_CHAT_URL, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        logger.warning(
            "openrouter_call_failed model=%s status=%s latency_ms=%s error_type=%s",
            model,
            status_code,
            latency_ms,
            exc.__class__.__name__,
        )
        if status_code == 401:
            raise AiServiceError("OpenRouter rejected the API key") from exc
        if status_code == 404:
            raise AiServiceError(
                "OpenRouter model endpoint not found. Set OPENROUTER_MODEL to an available model."
            ) from exc
        raise AiServiceError("OpenRouter request failed") from exc

    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "openrouter_call_succeeded model=%s status=%s latency_ms=%s",
        model,
        response.status_code,
        latency_ms,
    )

    body = response.json()
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AiServiceError("OpenRouter response missing choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise AiServiceError("OpenRouter response missing message")

    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AiServiceError("OpenRouter response missing content")

    return AiReply(ok=True, model=model, response=content.strip(), error=None)

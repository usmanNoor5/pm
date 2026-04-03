import os
from dataclasses import dataclass

import httpx

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.6-plus-preview:free"


class MissingApiKeyError(Exception):
    pass


class AiServiceError(Exception):
    pass


@dataclass
class AiReply:
    model: str
    answer: str


def request_ai_message(prompt: str) -> AiReply:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise MissingApiKeyError("OPENROUTER_API_KEY is not configured")

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
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
        raise AiServiceError("OpenRouter request failed") from exc

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

    return AiReply(model=model, answer=content.strip())

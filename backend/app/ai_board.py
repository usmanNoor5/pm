import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.db import BoardModel


class AiStructuredOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response: str = Field(min_length=1)
    board: BoardModel | None = None


def build_ai_board_prompt(
    *,
    user_message: str,
    conversation_history: list[dict[str, str]],
    current_board: BoardModel,
) -> str:
    board_json = json.dumps(current_board.model_dump(), ensure_ascii=True)
    history_json = json.dumps(conversation_history, ensure_ascii=True)

    return (
        "You are an assistant for a project management Kanban board.\n"
        "You must respond with strict JSON only (no markdown, no code fences).\n"
        "Return an object with this exact shape:\n"
        '{"response": "string", "board": null OR <valid board object>}\n'
        "Rules:\n"
        "- Keep response concise and useful.\n"
        "- If no board change is needed, set board to null.\n"
        "- If board change is needed, return the full updated board object with valid references.\n"
        "- Never return extra keys.\n"
        f"Conversation history JSON: {history_json}\n"
        f"Current board JSON: {board_json}\n"
        f"User message: {user_message}\n"
    )


def parse_ai_structured_output(raw_output: str) -> tuple[str, BoardModel | None, bool, str | None]:
    normalized = raw_output.strip()

    try:
        payload: Any = json.loads(normalized)
    except json.JSONDecodeError:
        return normalized, None, True, "AI output was not valid JSON; board unchanged"

    if not isinstance(payload, dict):
        return normalized, None, True, "AI output JSON must be an object; board unchanged"

    try:
        structured = AiStructuredOutput.model_validate(payload)
    except ValidationError:
        return normalized, None, True, "AI output did not match required schema; board unchanged"

    return structured.response.strip(), structured.board, False, None

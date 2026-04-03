import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


class CardModel(BaseModel):
    id: str = Field(min_length=1)
    title: str
    details: str


class ColumnModel(BaseModel):
    id: str = Field(min_length=1)
    title: str
    cardIds: list[str]


class BoardModel(BaseModel):
    columns: list[ColumnModel]
    cards: dict[str, CardModel]

    @model_validator(mode="after")
    def validate_card_references(self) -> "BoardModel":
        known_cards = set(self.cards.keys())
        for column in self.columns:
            for card_id in column.cardIds:
                if card_id not in known_cards:
                    raise ValueError(f"Column '{column.id}' references missing card '{card_id}'")
        return self


DEFAULT_BOARD = BoardModel(
    columns=[
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4", "card-5"]},
        {"id": "col-review", "title": "Review", "cardIds": ["card-6"]},
        {"id": "col-done", "title": "Done", "cardIds": ["card-7", "card-8"]},
    ],
    cards={
        "card-1": {
            "id": "card-1",
            "title": "Align roadmap themes",
            "details": "Draft quarterly themes with impact statements and metrics.",
        },
        "card-2": {
            "id": "card-2",
            "title": "Gather customer signals",
            "details": "Review support tags, sales notes, and churn feedback.",
        },
        "card-3": {
            "id": "card-3",
            "title": "Prototype analytics view",
            "details": "Sketch initial dashboard layout and key drill-downs.",
        },
        "card-4": {
            "id": "card-4",
            "title": "Refine status language",
            "details": "Standardize column labels and tone across the board.",
        },
        "card-5": {
            "id": "card-5",
            "title": "Design card layout",
            "details": "Add hierarchy and spacing for scanning dense lists.",
        },
        "card-6": {
            "id": "card-6",
            "title": "QA micro-interactions",
            "details": "Verify hover, focus, and loading states.",
        },
        "card-7": {
            "id": "card-7",
            "title": "Ship marketing page",
            "details": "Final copy approved and asset pack delivered.",
        },
        "card-8": {
            "id": "card-8",
            "title": "Close onboarding sprint",
            "details": "Document release notes and share internally.",
        },
    },
)


@dataclass
class DbConfig:
    db_path: Path


def get_db_config() -> DbConfig:
    configured = os.getenv("DATABASE_PATH")
    if configured:
        return DbConfig(db_path=Path(configured))
    default_path = Path(__file__).resolve().parents[1] / "data" / "app.db"
    return DbConfig(db_path=default_path)


def _connect() -> sqlite3.Connection:
    config = get_db_config()
    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL UNIQUE,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );

            CREATE TABLE IF NOT EXISTS boards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              name TEXT NOT NULL DEFAULT 'My Board',
              snapshot_json TEXT,
              snapshot_version INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
              UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS board_columns (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              board_id INTEGER NOT NULL,
              column_key TEXT NOT NULL,
              title TEXT NOT NULL,
              position INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
              UNIQUE (board_id, column_key),
              UNIQUE (board_id, position)
            );

            CREATE TABLE IF NOT EXISTS cards (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              board_id INTEGER NOT NULL,
              column_id INTEGER NOT NULL,
              card_key TEXT NOT NULL,
              title TEXT NOT NULL,
              details TEXT NOT NULL DEFAULT '',
              position INTEGER NOT NULL,
              created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
              FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
              FOREIGN KEY (column_id) REFERENCES board_columns(id) ON DELETE CASCADE,
              UNIQUE (board_id, card_key),
              UNIQUE (column_id, position)
            );

            CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id);
            CREATE INDEX IF NOT EXISTS idx_columns_board_id ON board_columns(board_id);
            CREATE INDEX IF NOT EXISTS idx_cards_board_id ON cards(board_id);
            CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id);
            """
        )
        _seed_default_user_board(conn)


def _seed_default_user_board(conn: sqlite3.Connection) -> None:
    user_id = _get_or_create_user_id(conn, "user")
    board_id = _get_or_create_board_id(conn, user_id)

    existing_columns = conn.execute(
        "SELECT COUNT(*) as c FROM board_columns WHERE board_id = ?", (board_id,)
    ).fetchone()["c"]
    if int(existing_columns) > 0:
        return

    _write_board(conn, board_id, DEFAULT_BOARD)


def _get_or_create_user_id(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return int(row["id"])

    cur = conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
    return int(cur.lastrowid)


def _get_or_create_board_id(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute("SELECT id FROM boards WHERE user_id = ? LIMIT 1", (user_id,)).fetchone()
    if row:
        return int(row["id"])

    cur = conn.execute(
        "INSERT INTO boards (user_id, name, snapshot_json, snapshot_version) VALUES (?, ?, NULL, 0)",
        (user_id, "My Board"),
    )
    return int(cur.lastrowid)


def get_board_for_user(username: str) -> BoardModel:
    with _connect() as conn:
        user_id = _get_or_create_user_id(conn, username)
        board_id = _get_or_create_board_id(conn, user_id)
        return _read_board(conn, board_id)


def replace_board_for_user(username: str, board: BoardModel) -> BoardModel:
    with _connect() as conn:
        user_id = _get_or_create_user_id(conn, username)
        board_id = _get_or_create_board_id(conn, user_id)
        _write_board(conn, board_id, board)
        return _read_board(conn, board_id)


def _read_board(conn: sqlite3.Connection, board_id: int) -> BoardModel:
    columns_rows = conn.execute(
        "SELECT id, column_key, title FROM board_columns WHERE board_id = ? ORDER BY position ASC",
        (board_id,),
    ).fetchall()

    cards_rows = conn.execute(
        "SELECT column_id, card_key, title, details FROM cards WHERE board_id = ? ORDER BY position ASC",
        (board_id,),
    ).fetchall()

    column_id_to_key: dict[int, str] = {int(row["id"]): str(row["column_key"]) for row in columns_rows}
    card_map: dict[str, CardModel] = {}
    cards_by_column_key: dict[str, list[str]] = {
        str(row["column_key"]): [] for row in columns_rows
    }

    for row in cards_rows:
        card_key = str(row["card_key"])
        card_map[card_key] = CardModel(
            id=card_key,
            title=str(row["title"]),
            details=str(row["details"]),
        )
        column_key = column_id_to_key[int(row["column_id"])]
        cards_by_column_key[column_key].append(card_key)

    columns = [
        ColumnModel(
            id=str(row["column_key"]),
            title=str(row["title"]),
            cardIds=cards_by_column_key[str(row["column_key"])],
        )
        for row in columns_rows
    ]

    return BoardModel(columns=columns, cards=card_map)


def _write_board(conn: sqlite3.Connection, board_id: int, board: BoardModel) -> None:
    with conn:
        conn.execute("DELETE FROM cards WHERE board_id = ?", (board_id,))
        conn.execute("DELETE FROM board_columns WHERE board_id = ?", (board_id,))

        column_pk_by_key: dict[str, int] = {}

        for column_position, column in enumerate(board.columns):
            cur = conn.execute(
                """
                INSERT INTO board_columns (board_id, column_key, title, position)
                VALUES (?, ?, ?, ?)
                """,
                (board_id, column.id, column.title, column_position),
            )
            column_pk_by_key[column.id] = int(cur.lastrowid)

        for column in board.columns:
            column_pk = column_pk_by_key[column.id]
            for card_position, card_id in enumerate(column.cardIds):
                card = board.cards[card_id]
                conn.execute(
                    """
                    INSERT INTO cards (board_id, column_id, card_key, title, details, position)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        board_id,
                        column_pk,
                        card.id,
                        card.title,
                        card.details,
                        card_position,
                    ),
                )

        conn.execute(
            """
            UPDATE boards
            SET snapshot_json = ?,
                snapshot_version = snapshot_version + 1,
                updated_at = (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            WHERE id = ?
            """,
            (json.dumps(board.model_dump()), board_id),
        )


def get_db_path() -> Path:
    return get_db_config().db_path


def db_exists() -> bool:
    return get_db_path().exists()


def get_raw_snapshot(username: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT b.snapshot_json
            FROM boards b
            JOIN users u ON u.id = b.user_id
            WHERE u.username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()
        if not row or row["snapshot_json"] is None:
            return None
        return json.loads(str(row["snapshot_json"]))

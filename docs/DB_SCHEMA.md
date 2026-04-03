# Database Schema Proposal (Part 5)

## Scope

This proposal defines a normalized SQLite schema for:
- users
- boards
- columns
- cards

It also includes an optional JSON snapshot strategy for fast whole-board reads and rollback/debug support.

## Design Goals

- Keep writes simple and explicit.
- Keep reads predictable for full-board payloads.
- Support future multi-user growth.
- Preserve MVP constraints:
  - login user is currently hardcoded (`user` / `password`)
  - one board per signed-in user for MVP

## Entity Model

- One user can own one or more boards (MVP uses one).
- One board has many columns.
- One column has many cards.
- Cards are ordered inside each column by `position`.
- Columns are ordered inside each board by `position`.

## Proposed SQLite DDL

```sql
PRAGMA foreign_keys = ON;

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
  -- Optional denormalized snapshot of full board JSON
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
```

## Why This Schema

- Normalized structure avoids JSON-only update complexity for common operations (rename column, move card, edit card).
- `position` fields make ordering deterministic without relying on array mutation in storage.
- `card_key` and `column_key` preserve stable public IDs for frontend/backend payloads.
- `snapshot_json` is optional and can be updated after successful transactional writes.

## Optional Snapshot Strategy

Two supported patterns:

1. Inline snapshot on `boards.snapshot_json` (recommended for MVP simplicity)
- On successful write transaction, regenerate full board payload and store in `snapshot_json`.
- Increment `snapshot_version`.

2. Separate history table (optional future extension)

```sql
CREATE TABLE IF NOT EXISTS board_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  snapshot_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
  UNIQUE (board_id, version)
);
```

For MVP, inline snapshot is enough and keeps code path shorter.

## Transaction Model

All board mutations should run in one DB transaction:
- Begin transaction
- Update normalized tables (`board_columns`, `cards`)
- Rebuild and write `snapshot_json` + increment `snapshot_version`
- Commit

If any step fails, rollback the whole mutation.

## Bootstrap and Migration Strategy

- DB file path: `backend/data/app.db` (create directory if missing).
- On backend startup:
  - ensure data directory exists
  - open SQLite connection
  - execute `PRAGMA foreign_keys = ON`
  - execute `CREATE TABLE IF NOT EXISTS ...` statements
  - seed default user (`user`) and one default board + five columns + starter cards if absent
- Migration approach for MVP:
  - store ordered SQL migration files in `backend/migrations/`
  - keep a `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT)` table
  - apply unapplied migrations at startup in lexical order

## Read/Write Tradeoff Summary

- Normalized reads require joins but are clear and robust.
- Snapshot provides fast single-read board payload for API responses.
- Snapshot may be slightly stale only if transaction discipline is broken; transaction model above prevents this.

## API Payload Alignment (for Parts 6-7)

Target board payload shape:

```json
{
  "board": {
    "id": "board-1",
    "columns": [
      { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1"] }
    ],
    "cards": {
      "card-1": { "id": "card-1", "title": "Task", "details": "Details" }
    }
  }
}
```

The relational model stores the same information explicitly, and snapshot can store this exact JSON structure.

## Recommendation

Approve the normalized schema with inline `snapshot_json` in `boards` for MVP.
If approved, Part 6 will implement:
- SQLite bootstrap
- seed data
- board read/update APIs
- tests for persistence and auth-protected access

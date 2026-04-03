# Frontend Agent Guide

## Scope

This file describes the current frontend-only Kanban demo in `frontend/` so future work can integrate it into the FastAPI + Docker architecture without losing existing behavior.

## Stack and Tooling

- Next.js 16 (App Router)
- React 19 + TypeScript
- Tailwind CSS v4
- `@dnd-kit` for drag and drop
- Vitest + Testing Library for unit/component tests
- Playwright for e2e tests
- ESLint via Next config

## Current App Structure

- `src/app/layout.tsx`
  - Loads Google fonts (`Space_Grotesk`, `Manrope`)
  - Applies global styles and metadata
- `src/app/page.tsx`
  - Renders `KanbanBoard` as the full homepage
- `src/app/globals.css`
  - Defines theme tokens and color variables
  - Includes the project color palette used by the UI

## Kanban Domain Model

- `src/lib/kanban.ts`
  - Types: `Card`, `Column`, `BoardData`
  - `initialData` with 5 fixed columns and seeded cards
  - `moveCard(columns, activeId, overId)` handles:
    - Reordering within a column
    - Moving across columns
    - Dropping onto column container (append behavior)
  - `createId(prefix)` creates client-side IDs for new cards

## UI Components

- `src/components/AuthApp.tsx`
  - Frontend auth gate for login/logout session flow
  - Calls backend auth APIs (`/api/auth/me`, `/api/auth/login`, `/api/auth/logout`)
  - Shows login form until authenticated, then renders `KanbanBoard`
- `src/components/KanbanBoard.tsx`
  - Client component and single source of UI state (`useState`)
  - Handles drag events, column rename, card add/delete
  - Uses `DndContext` + `DragOverlay`
  - Renders all 5 columns from current board state
- `src/components/KanbanColumn.tsx`
  - Droppable column container
  - Editable column title input
  - Sortable card list
  - New card form and empty-state drop hint
- `src/components/KanbanCard.tsx`
  - Sortable draggable card display with delete action
- `src/components/KanbanCardPreview.tsx`
  - Drag overlay preview for active card
- `src/components/NewCardForm.tsx`
  - Inline add-card UI with title/details inputs

## Current Behavior

- Board state is loaded from backend `GET /api/board` after login.
- Board mutations are persisted through backend `PUT /api/board`.
- Access to the board is gated behind backend session auth.
- Columns are fixed in count and order but titles are editable.
- Cards can be added, deleted, and moved with drag/drop.
- Auth session persists by cookie and board changes persist across reload.
- AI assistant is accessed via a floating button and compact chat panel (bottom-right) to avoid shrinking the board layout.
- AI chat calls backend `/api/ai/chat` and applies returned board updates live when `boardUpdated` is true.

## Test Coverage (Current)

- `src/lib/kanban.test.ts`
  - Unit tests for `moveCard` behavior
- `src/components/KanbanBoard.test.tsx`
  - Component tests for rendering, renaming, add/remove card
- `src/components/AuthApp.test.tsx`
  - Unit tests for unauthenticated login screen, successful sign-in transition, and AI chat board update application
- `tests/kanban.spec.ts`
  - E2E tests for auth-gated load, add card, drag/drop move, logout, persistence after reload, and AI chat-driven board updates

## Commands

- Install: `npm install`
- Dev server: `npm run dev`
- Unit tests: `npm run test:unit`
- E2E tests: `npm run test:e2e`
- All tests: `npm run test:all`

## Notes for Next Phases

- Preserve existing test IDs and interaction semantics where possible to reduce regression risk.
- During backend integration, move state ownership from local React state to API-driven fetch/mutate flows while keeping current UX behavior.
- Keep the current color token usage and visual tone consistent with root project requirements.

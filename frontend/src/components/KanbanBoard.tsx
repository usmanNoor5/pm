"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

type KanbanBoardProps = {
  initialBoard?: BoardData;
  disablePersistence?: boolean;
};

type BoardResponse = {
  board: BoardData;
};

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

type AiChatResponse = {
  ok: boolean;
  model?: string | null;
  response?: string | null;
  error?: string | null;
  board?: BoardData | null;
  boardUpdated?: boolean;
  fallbackUsed?: boolean;
};

export const KanbanBoard = ({
  initialBoard,
  disablePersistence = false,
}: KanbanBoardProps) => {
  const resolvedInitialBoard = initialBoard ?? (disablePersistence ? initialData : null);
  const [board, setBoard] = useState<BoardData | null>(resolvedInitialBoard);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(!resolvedInitialBoard);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [isChatSubmitting, setIsChatSubmitting] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const latestPersistRequestRef = useRef(0);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (disablePersistence) {
      return;
    }

    let cancelled = false;

    const loadBoard = async () => {
      try {
        const response = await fetch("/api/board", {
          credentials: "include",
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Failed to load board");
        }

        const payload = (await response.json()) as BoardResponse;
        if (!cancelled) {
          setBoard(payload.board);
          setSaveError(null);
        }
      } catch {
        if (!cancelled) {
          setSaveError("Unable to load board data.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadBoard();

    return () => {
      cancelled = true;
    };
  }, [disablePersistence]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);

  useEffect(() => {
    const el = chatScrollRef.current;
    if (!el) {
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [chatMessages]);

  const persistBoard = useCallback(
    async (nextBoard: BoardData, previousBoard: BoardData) => {
      const requestId = latestPersistRequestRef.current + 1;
      latestPersistRequestRef.current = requestId;

      try {
        const response = await fetch("/api/board", {
          method: "PUT",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ board: nextBoard }),
        });

        if (!response.ok) {
          throw new Error("Failed to save board");
        }

        const payload = (await response.json()) as BoardResponse;
        if (requestId === latestPersistRequestRef.current) {
          setBoard(payload.board);
          setSaveError(null);
        }
      } catch {
        if (requestId === latestPersistRequestRef.current) {
          setBoard(previousBoard);
          setSaveError("Could not save your latest board change.");
        }
      }
    },
    []
  );

  const applyBoardUpdate = useCallback(
    (updater: (prev: BoardData) => BoardData) => {
      setBoard((previous) => {
        if (!previous) {
          return previous;
        }
        const next = updater(previous);
        if (!disablePersistence) {
          void persistBoard(next, previous);
        }
        return next;
      });
    },
    [disablePersistence, persistBoard]
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    applyBoardUpdate((prev) => ({
      ...prev,
      columns: moveCard(prev.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((prev) => ({
      ...prev,
      columns: prev.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((prev) => ({
      ...prev,
      cards: {
        ...prev.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: prev.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((prev) => {
      return {
        ...prev,
        cards: Object.fromEntries(
          Object.entries(prev.cards).filter(([id]) => id !== cardId)
        ),
        columns: prev.columns.map((column) =>
          column.id === columnId
            ? {
                ...column,
                cardIds: column.cardIds.filter((id) => id !== cardId),
              }
            : column
        ),
      };
    });
  };

  const handleChatSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = chatInput.trim();
    if (!trimmed || !board || isChatSubmitting) {
      return;
    }

    const history = chatMessages.map((message) => ({
      role: message.role,
      content: message.content,
    }));

    setChatInput("");
    setChatError(null);
    setIsChatSubmitting(true);
    setChatMessages((previous) => [...previous, { role: "user", content: trimmed }]);

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: trimmed, history }),
      });

      const payload = (await response.json()) as AiChatResponse;

      if (!response.ok || !payload.ok) {
        const message = payload.error || "AI is temporarily unavailable.";
        setChatMessages((previous) => [
          ...previous,
          { role: "assistant", content: `I couldn't process that request: ${message}` },
        ]);
        setChatError(message);
        return;
      }

      if (payload.response) {
        setChatMessages((previous) => [
          ...previous,
          { role: "assistant", content: payload.response as string },
        ]);
      }

      if (payload.boardUpdated && payload.board) {
        setBoard(payload.board);
        setSaveError(null);
      }

      if (payload.error) {
        setChatError(payload.error);
      }
    } catch {
      setChatError("Unable to reach AI right now.");
      setChatMessages((previous) => [
        ...previous,
        { role: "assistant", content: "I couldn't reach the AI service right now. Please try again." },
      ]);
    } finally {
      setIsChatSubmitting(false);
    }
  };

  if (isLoading || !board) {
    return (
      <main className="grid min-h-screen place-items-center bg-[var(--surface)] px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
            </div>
          </div>
          {saveError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {saveError}
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <section className="grid gap-6 lg:grid-cols-5" data-testid="kanban-columns">
            {board.columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
              />
            ))}
          </section>
          <DragOverlay>
            {activeCard ? (
              <div className="w-[260px]">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>

        <button
          type="button"
          onClick={() => setIsChatOpen((value) => !value)}
          className="fixed bottom-6 right-6 z-40 rounded-full bg-[var(--secondary-purple)] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_28px_rgba(3,33,71,0.28)] transition hover:brightness-110"
          aria-label={isChatOpen ? "Close AI assistant" : "Open AI assistant"}
          data-testid="ai-chat-toggle"
        >
          {isChatOpen ? "Close AI" : "Ask AI"}
        </button>

        {isChatOpen ? (
          <aside
            className="fixed bottom-24 right-6 z-40 w-[min(420px,calc(100vw-3rem))] rounded-[24px] border border-[var(--stroke)] bg-white/95 p-5 shadow-[0_28px_52px_rgba(3,33,71,0.28)] backdrop-blur"
            data-testid="ai-chat-panel"
          >
            <div className="flex items-start justify-between gap-3 border-b border-[var(--stroke)] pb-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                  AI Assistant
                </p>
                <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
                  Board Chat
                </h2>
              </div>
              <span className="rounded-full border border-[var(--stroke)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)]">
                Live
              </span>
            </div>

            <div
              ref={chatScrollRef}
              className="mt-4 flex max-h-[360px] min-h-[180px] flex-col gap-3 overflow-y-auto pr-1"
              data-testid="ai-chat-messages"
            >
              {chatMessages.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] p-4 text-sm leading-6 text-[var(--gray-text)]">
                  Ask me to create, move, edit, or rename cards and columns. I can update the board directly.
                </div>
              ) : (
                chatMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={
                      message.role === "user"
                        ? "ml-6 rounded-2xl bg-[var(--secondary-purple)] px-4 py-3 text-sm leading-6 text-white"
                        : "mr-6 rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm leading-6 text-[var(--navy-dark)]"
                    }
                    data-testid={`chat-message-${message.role}`}
                  >
                    {message.content}
                  </div>
                ))
              )}
            </div>

            <form className="mt-4 flex flex-col gap-3" onSubmit={handleChatSubmit}>
              <label
                className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
                htmlFor="ai-message"
              >
                Message
              </label>
              <textarea
                id="ai-message"
                name="ai-message"
                rows={3}
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Try: Move card-1 to Review and rename Review to QA"
                className="resize-none rounded-2xl border border-[var(--stroke)] px-4 py-3 text-sm leading-6 outline-none ring-[var(--accent-yellow)] transition focus:ring-2"
                disabled={isChatSubmitting}
              />
              <button
                type="submit"
                disabled={isChatSubmitting || !chatInput.trim()}
                className="rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isChatSubmitting ? "Sending..." : "Send to AI"}
              </button>
            </form>

            {chatError ? (
              <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                {chatError}
              </p>
            ) : null}
          </aside>
        ) : null}
      </main>
    </div>
  );
};

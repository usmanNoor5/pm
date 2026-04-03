import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { AuthApp } from "@/components/AuthApp";
import { initialData } from "@/lib/kanban";

const fetchMock = vi.fn<typeof fetch>();

describe("AuthApp", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it("renders login form when unauthenticated", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ authenticated: false, username: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    render(<AuthApp />);

    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("logs in and shows kanban board", async () => {
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ authenticated: false, username: null }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ authenticated: true, username: "user" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ board: initialData }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    render(<AuthApp />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("heading", { name: /kanban studio/i })).toBeInTheDocument();
    expect(screen.getByText(/signed in as/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/auth/login",
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  it("applies board updates returned by AI chat", async () => {
    const updatedBoard = {
      ...initialData,
      columns: initialData.columns.map((column, index) =>
        index === 0 ? { ...column, title: "Inbox by AI" } : column
      ),
    };

    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ authenticated: false, username: null }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ authenticated: true, username: "user" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ board: initialData }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ok: true,
            model: "qwen/qwen3.6-plus:free",
            response: "Updated your first column title.",
            error: null,
            board: updatedBoard,
            boardUpdated: true,
            fallbackUsed: false,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        )
      );

    render(<AuthApp />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByRole("heading", { name: /kanban studio/i });
    await userEvent.click(screen.getByRole("button", { name: /open ai assistant/i }));

    await userEvent.type(
      screen.getByLabelText(/message/i),
      "Rename first column to Inbox by AI"
    );
    await userEvent.click(screen.getByRole("button", { name: /send to ai/i }));

    expect(await screen.findByDisplayValue("Inbox by AI")).toBeInTheDocument();
    expect(await screen.findByText(/updated your first column title/i)).toBeInTheDocument();
  });
});

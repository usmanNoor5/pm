"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";

type AuthState = {
  authenticated: boolean;
  username?: string | null;
};

const initialAuthState: AuthState = {
  authenticated: false,
  username: null,
};

export const AuthApp = () => {
  const [authState, setAuthState] = useState<AuthState>(initialAuthState);
  const [loading, setLoading] = useState(true);
  const [username, setUsername] = useState("user");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch("/api/auth/me", {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) {
          setAuthState(initialAuthState);
          return;
        }
        const payload = (await response.json()) as AuthState;
        setAuthState(payload);
      } catch {
        setAuthState(initialAuthState);
      } finally {
        setLoading(false);
      }
    };

    void checkSession();
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        setError("Invalid credentials. Use user / password.");
        setAuthState(initialAuthState);
        return;
      }

      const payload = (await response.json()) as AuthState;
      setAuthState(payload);
    } catch {
      setError("Unable to sign in right now. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setAuthState(initialAuthState);
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-[var(--surface)] px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          Loading workspace...
        </p>
      </main>
    );
  }

  if (!authState.authenticated) {
    return (
      <main className="relative grid min-h-screen place-items-center overflow-hidden bg-[var(--surface)] px-6">
        <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

        <section className="relative w-full max-w-md rounded-[28px] border border-[var(--stroke)] bg-white/85 p-8 shadow-[var(--shadow)] backdrop-blur">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Project Management MVP
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Sign in
          </h1>
          <p className="mt-2 text-sm text-[var(--gray-text)]">
            Use the demo credentials to access your kanban board.
          </p>

          <form className="mt-6 flex flex-col gap-4" onSubmit={handleLogin}>
            <label className="text-sm font-semibold text-[var(--navy-dark)]" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              name="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="rounded-xl border border-[var(--stroke)] px-4 py-3 text-sm outline-none ring-[var(--accent-yellow)] transition focus:ring-2"
              autoComplete="username"
              required
            />

            <label className="text-sm font-semibold text-[var(--navy-dark)]" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="rounded-xl border border-[var(--stroke)] px-4 py-3 text-sm outline-none ring-[var(--accent-yellow)] transition focus:ring-2"
              autoComplete="current-password"
              required
            />

            <button
              type="submit"
              disabled={submitting}
              className="mt-2 rounded-xl bg-[var(--secondary-purple)] px-4 py-3 text-sm font-semibold text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Signing in..." : "Sign in"}
            </button>
          </form>

          {error ? (
            <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <>
      <div className="sticky top-0 z-20 border-b border-[var(--stroke)] bg-white/85 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1500px] items-center justify-between px-6 py-3">
          <p className="text-sm font-semibold text-[var(--navy-dark)]">
            Signed in as <span className="text-[var(--primary-blue)]">{authState.username}</span>
          </p>
          <button
            type="button"
            onClick={handleLogout}
            disabled={submitting}
            className="rounded-lg border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-[var(--navy-dark)] transition hover:border-[var(--accent-yellow)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            Log out
          </button>
        </div>
      </div>
      <KanbanBoard />
    </>
  );
};

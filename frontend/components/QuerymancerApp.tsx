"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Menu, X } from "lucide-react";

import {
  AgentExhaustedError,
  postQueryStream,
  UnknownDatabaseError,
  UpstreamError,
} from "@/lib/api";
import type { Turn } from "@/lib/types";
import type { SuggestedQuestion } from "@/lib/suggestedQuestions";

import Atmosphere from "./Atmosphere";
import ChatPanel from "./ChatPanel";
import ResultsPanel from "./ResultsPanel";
import Sidebar from "./Sidebar";
import { Mark } from "./Ornament";

function newId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function QuerymancerApp() {
  const [databaseId, setDatabaseId] = useState("northwind");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const replaceTurn = useCallback((id: string, next: Turn) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? next : t)));
  }, []);

  // Switching database starts a fresh conversation. A session is bound
  // to one database_id on the backend; inlining prior turns from a
  // different schema would only confuse the model.
  const onChooseDatabase = useCallback(
    (next: string) => {
      if (next === databaseId) return;
      setDatabaseId(next);
      setTurns([]);
      setSessionId(null);
      setDraft("");
    },
    [databaseId],
  );

  const submit = useCallback(
    async (question: string) => {
      const id = newId();
      const pending: Turn = { id, kind: "pending", question };
      setTurns((prev) => [...prev, pending]);
      setLoading(true);
      setDraft("");

      // Live attempt indicator: as stream events arrive, mutate the
      // pending Turn so ChatPanel can render "self-correcting…
      // attempt N of 3 — fixing: <reason>".
      const onAttemptStart = (attempt: number) => {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === id && t.kind === "pending"
              ? { ...t, currentAttempt: attempt }
              : t,
          ),
        );
      };
      const onAttemptFail = (attempt: number, reason: string) => {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === id && t.kind === "pending"
              ? { ...t, currentAttempt: attempt, lastReason: reason }
              : t,
          ),
        );
      };

      try {
        const response = await postQueryStream(
          {
            question,
            database_id: databaseId,
            session_id: sessionId ?? undefined,
          },
          { onAttemptStart, onAttemptFail },
        );
        // Pin the session id on the very first successful turn; reuse
        // for the rest of the conversation.
        if (response.session_id && response.session_id !== sessionId) {
          setSessionId(response.session_id);
        }
        replaceTurn(id, { id, kind: "success", question, response });
      } catch (err) {
        if (err instanceof AgentExhaustedError) {
          replaceTurn(id, { id, kind: "exhausted", question, detail: err.detail });
        } else if (err instanceof UpstreamError) {
          replaceTurn(id, { id, kind: "exhausted", question, detail: err.detail });
        } else if (err instanceof UnknownDatabaseError) {
          replaceTurn(id, {
            id,
            kind: "error",
            question,
            error: `Unknown database: ${err.message}`,
          });
        } else if (err instanceof Error) {
          replaceTurn(id, { id, kind: "error", question, error: err.message });
        } else {
          replaceTurn(id, {
            id,
            kind: "error",
            question,
            error: "Unknown error contacting the backend.",
          });
        }
      } finally {
        setLoading(false);
      }
    },
    [databaseId, sessionId, replaceTurn],
  );

  const onChooseQuestion = useCallback(
    (q: SuggestedQuestion) => {
      setMobileSidebarOpen(false);
      void submit(q.text);
    },
    [submit],
  );

  const insertSnippet = useCallback((text: string) => {
    setDraft((prev) => {
      const trimmed = prev.trim();
      return trimmed ? `${trimmed} ${text}` : text;
    });
  }, []);

  // Auto-submit a question handed in via ?q= (from the landing hero)
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const handoffConsumed = useRef(false);
  useEffect(() => {
    if (handoffConsumed.current) return;
    const q = searchParams.get("q")?.trim();
    if (!q) return;
    handoffConsumed.current = true;
    void submit(q);
    router.replace(pathname);
  }, [searchParams, submit, router, pathname]);

  // Close mobile sidebar on Escape
  useEffect(() => {
    if (!mobileSidebarOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileSidebarOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mobileSidebarOpen]);

  const latestTurn = turns.length > 0 ? turns[turns.length - 1] : null;

  return (
    <div className="relative min-h-dvh">
      <Atmosphere />

      <div className="relative z-10 flex flex-col h-dvh">
        <Header
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />

        <main className="grid flex-1 min-h-0 grid-cols-1 md:grid-cols-[280px_1fr] lg:grid-cols-[280px_1fr_440px]">
          {/* Sidebar — desktop (md+) */}
          <motion.div
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.18, duration: 0.4, ease: "easeOut" }}
            className="hidden md:block min-h-0 overflow-y-auto"
          >
            <Sidebar
              databaseId={databaseId}
              onChooseDatabase={onChooseDatabase}
              onChooseQuestion={onChooseQuestion}
              onInsertSnippet={insertSnippet}
            />
          </motion.div>

          {/* Chat */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28, duration: 0.45, ease: "easeOut" }}
            className="min-h-0 border-l border-r border-white/[0.06]"
          >
            <ChatPanel
              turns={turns}
              loading={loading}
              onSubmit={submit}
              draft={draft}
              onDraftChange={setDraft}
            />
          </motion.div>

          {/* Results — lg+ */}
          <motion.div
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.38, duration: 0.45, ease: "easeOut" }}
            className="hidden lg:block min-h-0 overflow-y-auto"
          >
            <ResultsPanel turn={latestTurn} />
          </motion.div>
        </main>
      </div>

      {/* Mobile sidebar drawer */}
      <AnimatePresence>
        {mobileSidebarOpen && (
          <motion.div
            key="mobile-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-40 bg-zinc-950/70 backdrop-blur-sm md:hidden"
            onClick={() => setMobileSidebarOpen(false)}
          />
        )}
        {mobileSidebarOpen && (
          <motion.aside
            key="mobile-drawer"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
            className="fixed left-0 top-0 bottom-0 z-50 w-[300px] max-w-[85vw]
                       bg-zinc-950 border-r border-white/[0.08] md:hidden
                       overflow-y-auto"
          >
            <div className="flex justify-end p-3">
              <button
                onClick={() => setMobileSidebarOpen(false)}
                className="p-2 rounded text-zinc-500 hover:text-zinc-100"
                aria-label="Close menu"
              >
                <X className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>
            <Sidebar
              databaseId={databaseId}
              onChooseDatabase={(id) => {
                onChooseDatabase(id);
                setMobileSidebarOpen(false);
              }}
              onChooseQuestion={onChooseQuestion}
              onInsertSnippet={(text) => {
                insertSnippet(text);
                setMobileSidebarOpen(false);
              }}
            />
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
}

function Header({
  onOpenMobileSidebar,
}: {
  onOpenMobileSidebar: () => void;
}) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="relative flex items-center justify-between px-5 sm:px-8 py-4
                 border-b border-white/[0.06] bg-ink/80 backdrop-blur-xl"
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden p-1.5 -ml-1.5 rounded text-zinc-400 hover:text-zinc-100 transition-colors"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" strokeWidth={1.5} />
        </button>
        <Link
          href="/"
          className="flex items-center gap-3 group"
          aria-label="Back to Querymancer landing"
        >
          <Mark className="w-6 h-6 text-accent transition-transform group-hover:scale-110" />
          <div className="leading-tight">
            <h1 className="text-zinc-50 text-[15px] font-medium tracking-tight group-hover:text-accent transition-colors">
              Querymancer
            </h1>
            <p className="text-[10px] tracking-[0.18em] uppercase text-zinc-400 mt-0.5 font-mono">
              natural language → sql
            </p>
          </div>
        </Link>
      </div>

      <nav className="flex items-center gap-4 sm:gap-6 text-[11px] font-mono">
        <span className="hidden md:flex items-center gap-2 text-zinc-400">
          <span className="relative flex h-2 w-2">
            <span className="absolute inset-0 rounded-full bg-success opacity-60 animate-ping" />
            <span className="relative h-2 w-2 rounded-full bg-success" />
          </span>
          backend online
        </span>
        <span className="text-zinc-500 tracking-[0.18em] uppercase whitespace-nowrap">
          v1.0 · phase vii
        </span>
      </nav>
    </motion.header>
  );
}

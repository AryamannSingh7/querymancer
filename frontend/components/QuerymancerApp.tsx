"use client";

import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Menu, X } from "lucide-react";

import {
  AgentExhaustedError,
  postQuery,
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
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState("");
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const replaceTurn = useCallback((id: string, next: Turn) => {
    setTurns((prev) => prev.map((t) => (t.id === id ? next : t)));
  }, []);

  const submit = useCallback(
    async (question: string) => {
      const id = newId();
      const pending: Turn = { id, kind: "pending", question };
      setTurns((prev) => [...prev, pending]);
      setLoading(true);
      setDraft("");

      try {
        const response = await postQuery({ question, database_id: databaseId });
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
    [databaseId, replaceTurn],
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
              onChooseDatabase={setDatabaseId}
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
                setDatabaseId(id);
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
                 border-b border-white/[0.06] bg-base/80 backdrop-blur-xl"
    >
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobileSidebar}
          className="md:hidden p-1.5 -ml-1.5 rounded text-zinc-400 hover:text-zinc-100 transition-colors"
          aria-label="Open menu"
        >
          <Menu className="w-5 h-5" strokeWidth={1.5} />
        </button>
        <Mark className="w-6 h-6 text-accent" />
        <div className="leading-tight">
          <h1 className="text-zinc-100 text-[15px] font-medium tracking-tight">
            Querymancer
          </h1>
          <p className="text-[10px] tracking-[0.18em] uppercase text-zinc-500 mt-0.5 font-mono">
            natural language → sql
          </p>
        </div>
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
          v0.4 · phase iv
        </span>
      </nav>
    </motion.header>
  );
}

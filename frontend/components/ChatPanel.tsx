"use client";

import { FormEvent, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Loader2 } from "lucide-react";

import type { Turn } from "@/lib/types";
import SqlBlock from "./SqlBlock";

interface ChatPanelProps {
  turns: Turn[];
  loading: boolean;
  onSubmit: (question: string) => void;
  draft: string;
  onDraftChange: (s: string) => void;
}

export default function ChatPanel({
  turns,
  loading,
  onSubmit,
  draft,
  onDraftChange,
}: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [turns.length, turns[turns.length - 1]?.kind]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
  };

  return (
    <section className="relative flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-10 pt-12 pb-6">
        {turns.length === 0 ? <Welcome /> : null}

        <ol className="space-y-10 max-w-2xl mx-auto">
          <AnimatePresence initial={false}>
            {turns.map((t) => (
              <motion.li
                key={t.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: "easeOut" }}
              >
                <TurnView turn={t} />
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      </div>

      <Composer
        loading={loading}
        draft={draft}
        onDraftChange={onDraftChange}
        onSubmit={handleSubmit}
      />
    </section>
  );
}

/* ------------------------------------------------------------------ */

function Welcome() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25, duration: 0.5 }}
      className="max-w-xl mx-auto text-center pt-8 pb-14"
    >
      <h1 className="text-zinc-100 text-[40px] leading-[1.05] font-medium tracking-tight mb-4">
        Ask your data
        <span className="text-accent">.</span>
      </h1>
      <p className="text-[14px] text-zinc-400 leading-relaxed max-w-md mx-auto">
        Pose a question in plain English. Querymancer retrieves the relevant
        schema chunks, generates SQL with Gemini, runs it read-only against the
        bound database, and shows you the result.
      </p>
    </motion.div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  return (
    <article className="space-y-4">
      {/* User question */}
      <header className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-2 inline-block h-px w-6 bg-accent flex-shrink-0"
        />
        <p className="text-zinc-100 text-[20px] leading-snug font-medium">
          {turn.question}
        </p>
      </header>

      {/* Backend response */}
      {turn.kind === "pending" && (
        <div className="ml-9 flex items-center gap-2.5 text-zinc-500 text-[13px]">
          <Loader2
            className="w-3.5 h-3.5 animate-spin text-accent"
            strokeWidth={1.5}
          />
          <span className="eyebrow pulse-soft">thinking</span>
        </div>
      )}

      {turn.kind === "success" && (
        <div className="ml-9 space-y-4">
          <SqlBlock sql={turn.response.sql} />
          <p className="text-[13px] leading-relaxed text-zinc-400">
            {turn.response.explanation}
          </p>
          {turn.response.attempts > 1 && (
            <p className="eyebrow text-warn">
              self-corrected · {turn.response.attempts} attempts
            </p>
          )}
        </div>
      )}

      {turn.kind === "exhausted" && (
        <div className="ml-9 space-y-2">
          <p className="eyebrow text-error">retry budget exhausted</p>
          <p className="text-[13px] text-zinc-300 leading-relaxed">
            {turn.detail.message}
          </p>
          <p className="text-[11px] text-zinc-500 font-mono">
            {turn.detail.attempts} attempts — see the panel for details.
          </p>
        </div>
      )}

      {turn.kind === "error" && (
        <div className="ml-9">
          <p className="eyebrow text-error mb-1.5">request failed</p>
          <p className="text-[13px] text-zinc-300 leading-relaxed font-mono">
            {turn.error}
          </p>
        </div>
      )}
    </article>
  );
}

function Composer({
  loading,
  draft,
  onDraftChange,
  onSubmit,
}: {
  loading: boolean;
  draft: string;
  onDraftChange: (s: string) => void;
  onSubmit: (e: FormEvent) => void;
}) {
  return (
    <div className="border-t border-white/[0.06] bg-ink/80 backdrop-blur-xl">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <form onSubmit={onSubmit} className="relative">
          <div
            className="flex items-end gap-2 surface rounded-xl px-4 py-3
                       focus-within:border-accent/50 transition-colors"
          >
            <textarea
              value={draft}
              onChange={(e) => onDraftChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e as unknown as FormEvent);
                }
              }}
              placeholder="Ask your data…"
              disabled={loading}
              rows={1}
              className="flex-1 bg-transparent text-zinc-100 placeholder:text-zinc-600
                         focus:outline-none text-[14px] resize-none
                         disabled:opacity-50 leading-relaxed py-1"
              aria-label="Question"
              autoFocus
            />
            <button
              type="submit"
              disabled={!draft.trim() || loading}
              className="flex items-center justify-center w-8 h-8 rounded-md
                         bg-accent text-ink hover:bg-accent-soft
                         disabled:bg-zinc-800 disabled:text-zinc-600
                         disabled:cursor-not-allowed transition-all"
              aria-label="Send"
            >
              {loading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={2} />
              ) : (
                <ArrowUp className="w-4 h-4" strokeWidth={2.5} />
              )}
            </button>
          </div>

          <p className="mt-2.5 text-center text-[10px] font-mono tracking-[0.18em] uppercase text-zinc-600">
            ↩ to send · shift+↩ for newline · queries run read-only
          </p>
        </form>
      </div>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowRight } from "lucide-react";

export default function HeroQueryForm() {
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const trimmed = draft.trim();

  function go(question: string) {
    const q = question.trim();
    if (!q) return;
    router.push(`/app?q=${encodeURIComponent(q)}`);
  }

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    go(draft);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      go(draft);
    }
  }

  return (
    <form
      action="/app"
      method="GET"
      onSubmit={onSubmit}
      className="group relative"
    >
      <div
        className="surface rounded-2xl ring-1 ring-white/[0.04]
                   focus-within:ring-accent/30 focus-within:shadow-[0_0_0_4px_rgba(197,245,0,0.04)]
                   transition-all"
      >
        <div className="flex items-end gap-2 p-2 sm:p-3">
          <textarea
            name="q"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="e.g. Top 5 product categories by total revenue"
            rows={2}
            spellCheck={false}
            autoComplete="off"
            className="flex-1 resize-none bg-transparent px-3 py-3 sm:px-4 sm:py-3.5
                       text-[15px] sm:text-base text-zinc-100 placeholder-zinc-600
                       outline-none font-light leading-relaxed"
          />
          <button
            type="submit"
            disabled={!trimmed}
            className="m-1 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl
                       bg-accent text-ink font-mono text-[12px] uppercase tracking-[0.18em]
                       hover:bg-accent-soft hover:shadow-[0_0_24px_-6px_rgba(197,245,0,0.6)]
                       disabled:opacity-30 disabled:hover:bg-accent disabled:hover:shadow-none
                       disabled:cursor-not-allowed
                       transition-all"
          >
            <span className="hidden sm:inline">Run</span>
            <ArrowRight className="w-4 h-4" strokeWidth={2.2} />
          </button>
        </div>
      </div>
      <p className="mt-3 text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-600">
        Press <span className="text-zinc-400">enter</span> to run · Shift + enter for newline
      </p>
    </form>
  );
}

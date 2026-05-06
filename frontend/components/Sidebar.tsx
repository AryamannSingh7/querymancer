"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Database, Sparkles, Table2 } from "lucide-react";

import {
  DEMO_DATABASES,
  SUGGESTED_QUESTIONS,
  type SuggestedQuestion,
} from "@/lib/suggestedQuestions";
import SchemaBrowser from "./SchemaBrowser";

interface SidebarProps {
  databaseId: string;
  onChooseDatabase: (id: string) => void;
  onChooseQuestion: (q: SuggestedQuestion) => void;
  onInsertSnippet?: (text: string) => void;
}

type Tab = "try" | "schema";

export default function Sidebar({
  databaseId,
  onChooseDatabase,
  onChooseQuestion,
  onInsertSnippet,
}: SidebarProps) {
  const [tab, setTab] = useState<Tab>("try");
  const questions = SUGGESTED_QUESTIONS[databaseId] ?? [];
  const dbName =
    DEMO_DATABASES.find((d) => d.id === databaseId)?.name ?? databaseId;

  return (
    <aside className="relative flex flex-col gap-6 px-6 py-7 h-full min-h-0">
      {/* Database selector */}
      <section>
        <header className="flex items-center gap-2 mb-3">
          <Database className="w-3.5 h-3.5 text-zinc-500" strokeWidth={1.5} />
          <h2 className="eyebrow">Database</h2>
        </header>

        <div className="space-y-1.5">
          {DEMO_DATABASES.map((d) => {
            const active = d.id === databaseId;
            return (
              <button
                key={d.id}
                onClick={() => onChooseDatabase(d.id)}
                className={`row-hover w-full text-left rounded-md border px-3.5 py-3 ${
                  active
                    ? "border-accent/50 bg-accent/[0.06] text-zinc-100"
                    : "border-white/[0.06] bg-surface text-zinc-300"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[14px] font-medium leading-none">
                    {d.name}
                  </span>
                  <span
                    className={`text-[10px] font-mono tracking-[0.16em] uppercase ${
                      active ? "text-accent" : "text-zinc-500"
                    }`}
                  >
                    {d.tableCount} tables
                  </span>
                </div>
                <p className="text-[12px] text-zinc-500 leading-snug">
                  {d.blurb}
                </p>
              </button>
            );
          })}
        </div>
      </section>

      {/* Tab toggle */}
      <div className="flex items-center gap-1 -mb-1">
        <TabButton
          active={tab === "try"}
          onClick={() => setTab("try")}
          icon={<Sparkles className="w-3 h-3" strokeWidth={1.5} />}
          label="try"
        />
        <TabButton
          active={tab === "schema"}
          onClick={() => setTab("schema")}
          icon={<Table2 className="w-3 h-3" strokeWidth={1.5} />}
          label="schema"
        />
      </div>

      {/* Tab body — scrollable */}
      <section className="flex-1 min-h-0 overflow-y-auto -mx-1 px-1">
        {tab === "try" ? (
          <ul className="space-y-0.5">
            {questions.map((q, i) => (
              <motion.li
                key={q.id}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.04, duration: 0.3 }}
              >
                <button
                  onClick={() => onChooseQuestion(q)}
                  className="row-hover group w-full text-left rounded-md border border-transparent
                             px-3 py-2.5 text-[13px] leading-snug text-zinc-400 hover:text-zinc-100"
                >
                  <span className="block">{q.text}</span>
                  <span
                    className="mt-1.5 inline-block text-[9px] font-mono tracking-[0.2em] uppercase
                               text-zinc-600 group-hover:text-accent transition-colors"
                  >
                    {q.hint}
                  </span>
                </button>
              </motion.li>
            ))}
          </ul>
        ) : (
          <motion.div
            key="schema"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <SchemaBrowser
              databaseId={databaseId}
              databaseName={dbName}
              onInsertColumn={onInsertSnippet}
            />
          </motion.div>
        )}
      </section>

      <footer className="text-[10px] font-mono tracking-[0.16em] uppercase text-zinc-600">
        read-only · gemini 2.5 flash · pgvector
      </footer>
    </aside>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[10px]
                  font-mono tracking-[0.18em] uppercase transition-all
                  ${
                    active
                      ? "bg-accent/[0.1] text-accent"
                      : "text-zinc-500 hover:text-zinc-200"
                  }`}
    >
      {icon}
      {label}
    </button>
  );
}

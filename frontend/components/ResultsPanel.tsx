"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ChartColumn, Loader2, Table2 } from "lucide-react";

import type { Turn } from "@/lib/types";
import ChartRenderer from "./ChartRenderer";
import ResultsTable from "./ResultsTable";

type Tab = "chart" | "table";

interface ResultsPanelProps {
  turn: Turn | null;
}

export default function ResultsPanel({ turn }: ResultsPanelProps) {
  const [tab, setTab] = useState<Tab>("chart");

  useEffect(() => {
    if (turn?.kind === "success") {
      setTab(turn.response.chart_hint === "table" ? "table" : "chart");
    }
  }, [turn]);

  if (!turn) return <EmptyState />;
  if (turn.kind === "pending") return <PendingState question={turn.question} />;
  if (turn.kind === "error") return <ErrorState message={turn.error} />;
  if (turn.kind === "exhausted") {
    return (
      <ErrorState
        message={turn.detail.message}
        attempts={turn.detail.attempts}
        errors={turn.detail.errors}
      />
    );
  }

  const { response } = turn;

  return (
    <section className="relative flex flex-col h-full">
      <header className="flex items-center justify-between px-6 pt-7 pb-5">
        <div>
          <p className="eyebrow mb-1.5">Result</p>
          <h2 className="text-zinc-100 text-[22px] font-medium leading-tight tracking-tight">
            {response.rows.length} row{response.rows.length === 1 ? "" : "s"}
            <span className="text-zinc-500"> · {response.columns.length} col
              {response.columns.length === 1 ? "" : "s"}</span>
          </h2>
        </div>
        <div className="text-right">
          <p className="eyebrow-accent">ok</p>
          <p className="text-[10px] text-zinc-500 mt-1 font-mono">
            {response.attempts} attempt{response.attempts === 1 ? "" : "s"}
          </p>
        </div>
      </header>

      <div className="hr-soft mx-6" />

      {/* Tabs */}
      <div className="px-6 pt-4 pb-3 flex gap-1">
        <TabButton
          active={tab === "chart"}
          onClick={() => setTab("chart")}
          icon={<ChartColumn className="w-3.5 h-3.5" strokeWidth={1.5} />}
          label="chart"
        />
        <TabButton
          active={tab === "table"}
          onClick={() => setTab("table")}
          icon={<Table2 className="w-3.5 h-3.5" strokeWidth={1.5} />}
          label="table"
        />
        {response.chart_hint !== "table" && (
          <span className="ml-auto text-[10px] font-mono tracking-[0.18em] uppercase text-zinc-600 self-center">
            hint · {response.chart_hint}
          </span>
        )}
      </div>

      {/* Body */}
      <motion.div
        key={`${turn.id}-${tab}`}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex-1 mx-6 mb-6 overflow-auto surface rounded-lg"
      >
        {tab === "chart" ? (
          <ChartRenderer
            chartHint={response.chart_hint}
            columns={response.columns}
            rows={response.rows}
          />
        ) : (
          <ResultsTable
            columns={response.columns}
            rows={response.rows}
          />
        )}
      </motion.div>
    </section>
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
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[11px]
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

function EmptyState() {
  return (
    <section className="relative flex flex-col items-center justify-center h-full px-10">
      <div className="text-center max-w-sm">
        <div className="hr-soft w-12 mx-auto mb-6" />
        <p className="eyebrow mb-3">Result</p>
        <h2 className="text-zinc-300 text-[20px] font-medium leading-snug mb-3">
          Ready when you are.
        </h2>
        <p className="text-[13px] text-zinc-500 leading-relaxed">
          Ask a question in the chat. The result table and a suggested chart
          will appear here.
        </p>
      </div>
    </section>
  );
}

function PendingState({ question }: { question: string }) {
  return (
    <section className="relative flex flex-col items-center justify-center h-full px-10">
      <div className="text-center max-w-sm">
        <Loader2
          className="w-5 h-5 animate-spin text-accent mx-auto mb-5"
          strokeWidth={1.5}
        />
        <p className="eyebrow pulse-soft mb-3">retrieving · generating · executing</p>
        <p className="text-zinc-400 text-[14px] leading-snug">
          “{question}”
        </p>
      </div>
    </section>
  );
}

function ErrorState({
  message,
  attempts,
  errors,
}: {
  message: string;
  attempts?: number;
  errors?: string[];
}) {
  return (
    <section className="relative flex flex-col items-center justify-center h-full px-8">
      <div className="text-center max-w-md">
        <p className="eyebrow text-error mb-4">error</p>
        <h2 className="text-zinc-100 text-[18px] font-medium leading-snug mb-3">
          {message}
        </h2>
        {attempts !== undefined && (
          <p className="text-[10px] font-mono tracking-[0.18em] uppercase text-zinc-500 mb-4">
            {attempts} attempt{attempts === 1 ? "" : "s"}
          </p>
        )}
        {errors && errors.length > 0 && (
          <details className="text-left mt-5 text-[12px] text-zinc-400 surface rounded-md p-4">
            <summary className="cursor-pointer text-accent hover:text-accent-soft mb-2 text-[11px] font-mono tracking-[0.18em] uppercase">
              error trail ({errors.length})
            </summary>
            <ol className="list-decimal list-inside space-y-2 leading-relaxed font-mono text-[11px] mt-3">
              {errors.map((e, i) => (
                <li key={i} className="text-zinc-400 break-words">
                  {e}
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
    </section>
  );
}

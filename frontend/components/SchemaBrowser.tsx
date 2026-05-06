"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronRight, KeyRound, Link2, Loader2, Network } from "lucide-react";

import { getSchema } from "@/lib/api";
import type { SchemaTable } from "@/lib/types";
import SchemaDiagram from "./SchemaDiagram";

interface SchemaBrowserProps {
  databaseId: string;
  databaseName: string;
  onInsertColumn?: (snippet: string) => void;
}

export default function SchemaBrowser({
  databaseId,
  databaseName,
  onInsertColumn,
}: SchemaBrowserProps) {
  const [tables, setTables] = useState<SchemaTable[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openName, setOpenName] = useState<string | null>(null);
  const [diagramOpen, setDiagramOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setTables(null);
    setError(null);
    setOpenName(null);

    getSchema(databaseId)
      .then((data) => {
        if (cancelled) return;
        setTables(data);
        // Open the largest table by default — usually the most useful
        const biggest = [...data].sort((a, b) => b.row_count - a.row_count)[0];
        if (biggest) setOpenName(biggest.name);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      });

    return () => {
      cancelled = true;
    };
  }, [databaseId]);

  if (error) {
    return (
      <div className="text-[12px] text-error font-mono leading-relaxed">
        {error}
      </div>
    );
  }

  if (!tables) {
    return (
      <div className="flex items-center gap-2 text-zinc-500 text-[12px]">
        <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
        loading schema…
      </div>
    );
  }

  return (
    <>
      <button
        onClick={() => setDiagramOpen(true)}
        className="w-full flex items-center justify-center gap-2 mb-3 px-3 py-2.5
                   rounded-md border border-accent/30 bg-accent/[0.05] text-accent
                   text-[11px] font-mono tracking-[0.18em] uppercase
                   hover:bg-accent hover:text-zinc-950 hover:border-accent
                   transition-all"
      >
        <Network className="w-3.5 h-3.5" strokeWidth={1.5} />
        view diagram
      </button>

      <ul className="space-y-1">
        {tables.map((t) => (
          <li key={t.name}>
            <TableRow
              table={t}
              open={openName === t.name}
              onToggle={() =>
                setOpenName((prev) => (prev === t.name ? null : t.name))
              }
            />
          </li>
        ))}
      </ul>

      {diagramOpen && (
        <SchemaDiagram
          databaseName={databaseName}
          tables={tables}
          onClose={() => setDiagramOpen(false)}
          onInsertColumn={onInsertColumn}
        />
      )}
    </>
  );
}

function TableRow({
  table,
  open,
  onToggle,
}: {
  table: SchemaTable;
  open: boolean;
  onToggle: () => void;
}) {
  const empty = table.row_count === 0;
  return (
    <div className="rounded-md border border-white/[0.06] overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2 text-left
                   hover:bg-white/[0.03] transition-colors"
      >
        <ChevronRight
          className={`w-3 h-3 text-zinc-500 transition-transform ${
            open ? "rotate-90" : ""
          }`}
          strokeWidth={2}
        />
        <span
          className={`flex-1 text-[12.5px] font-medium ${
            empty ? "text-zinc-500 italic" : "text-zinc-200"
          }`}
        >
          {table.name}
        </span>
        <span className="text-[9px] font-mono tracking-[0.16em] uppercase text-zinc-500">
          {table.row_count.toLocaleString()}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="overflow-hidden border-t border-white/[0.04]"
          >
            <ColumnList table={table} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ColumnList({ table }: { table: SchemaTable }) {
  const fkByCol = new Map(table.foreign_keys.map((fk) => [fk.from_col, fk]));

  return (
    <div className="px-3 py-2.5 space-y-1.5">
      {table.columns.map((c) => {
        const fk = fkByCol.get(c.name);
        return (
          <div
            key={c.name}
            className="flex items-baseline gap-2 text-[11.5px] font-mono leading-snug"
          >
            <span className="flex items-center gap-1 min-w-0 flex-1">
              {c.pk ? (
                <KeyRound
                  className="w-2.5 h-2.5 text-accent flex-shrink-0"
                  strokeWidth={2}
                />
              ) : fk ? (
                <Link2
                  className="w-2.5 h-2.5 text-zinc-400 flex-shrink-0"
                  strokeWidth={2}
                />
              ) : (
                <span className="w-2.5 inline-block flex-shrink-0" />
              )}
              <span className={c.pk ? "text-accent" : "text-zinc-200"}>
                {c.name}
              </span>
            </span>
            <span className="text-zinc-500 text-[10px] uppercase tracking-wide flex-shrink-0">
              {c.type.toLowerCase()}
            </span>
          </div>
        );
      })}

      {table.foreign_keys.length > 0 && (
        <div className="pt-2 mt-2 border-t border-white/[0.04]">
          <p className="text-[9px] font-mono tracking-[0.16em] uppercase text-zinc-500 mb-1.5">
            references
          </p>
          {table.foreign_keys.map((fk, i) => (
            <p
              key={i}
              className="text-[11px] font-mono text-zinc-400 leading-snug"
            >
              <span className="text-zinc-200">{fk.from_col}</span>
              <span className="text-zinc-600"> → </span>
              <span className="text-zinc-300">{fk.to_table}</span>
              <span className="text-zinc-600">.</span>
              <span className="text-zinc-300">{fk.to_col}</span>
            </p>
          ))}
        </div>
      )}

      {table.referenced_by.length > 0 && (
        <div className="pt-2 mt-2 border-t border-white/[0.04]">
          <p className="text-[9px] font-mono tracking-[0.16em] uppercase text-zinc-500 mb-1.5">
            referenced by
          </p>
          {table.referenced_by.map((ref, i) => (
            <p
              key={i}
              className="text-[11px] font-mono text-zinc-400 leading-snug"
            >
              <span className="text-zinc-300">{ref.to_table}</span>
              <span className="text-zinc-600">.</span>
              <span className="text-zinc-300">{ref.from_col}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

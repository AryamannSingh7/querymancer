"use client";

import { motion } from "motion/react";

interface ResultsTableProps {
  columns: string[];
  rows: unknown[][];
}

function formatCell(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString();
    return v.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    });
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export default function ResultsTable({ columns, rows }: ResultsTableProps) {
  if (rows.length === 0) {
    return (
      <div className="px-6 py-12 text-center text-zinc-500 text-[13px]">
        Empty result — query returned no rows.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-white/[0.08]">
            {columns.map((c) => (
              <th
                key={c}
                className="px-4 py-3 text-left eyebrow whitespace-nowrap"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <motion.tr
              key={i}
              initial={{ opacity: 0, y: 3 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.02, duration: 0.25 }}
              className="border-b border-white/[0.04] hover:bg-accent/[0.04] transition-colors"
            >
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="px-4 py-2.5 text-zinc-300 whitespace-nowrap font-mono"
                >
                  {formatCell(cell)}
                </td>
              ))}
            </motion.tr>
          ))}
        </tbody>
      </table>

      <div className="px-4 py-2.5 border-t border-white/[0.06] text-[10px] font-mono tracking-[0.18em] uppercase text-zinc-600">
        {rows.length} row{rows.length === 1 ? "" : "s"} · {columns.length} column
        {columns.length === 1 ? "" : "s"}
      </div>
    </div>
  );
}

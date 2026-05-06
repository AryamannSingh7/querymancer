"use client";

import { motion } from "motion/react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ChartHint } from "@/lib/types";

/**
 * Console palette — single bright accent + greyscale tones.
 * Pie/bar use a graduated lime-to-zinc ramp so categories
 * stay distinguishable without the chart turning into confetti.
 */
const PALETTE = [
  "#c5f500", // accent
  "#a3cf00", // accent dark
  "#e2fa7a", // accent soft
  "#a1a1aa", // zinc-400
  "#71717a", // zinc-500
  "#52525b", // zinc-600
  "#3f3f46", // zinc-700
  "#27272a", // zinc-800
];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: "rgba(9, 9, 11, 0.95)",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  borderRadius: 6,
  padding: "8px 12px",
  fontFamily: "var(--font-mono)",
  fontSize: 12,
  color: "#e4e4e7",
  boxShadow: "0 12px 32px -8px rgba(0,0,0,0.7)",
};

const TOOLTIP_LABEL_STYLE: React.CSSProperties = {
  color: "#c5f500",
  textTransform: "uppercase",
  letterSpacing: "0.16em",
  fontSize: 9,
  marginBottom: 4,
};

const TOOLTIP_ITEM_STYLE: React.CSSProperties = {
  color: "#f4f4f5",
};

const AXIS_TICK = {
  fill: "#a1a1aa",
  fontSize: 11,
  fontFamily: "var(--font-mono)",
};

type Datum = Record<string, unknown>;

function toData(columns: string[], rows: unknown[][]): Datum[] {
  return rows.map((row) => {
    const obj: Datum = {};
    columns.forEach((c, i) => {
      obj[c] = row[i];
    });
    return obj;
  });
}

function pickAxes(columns: string[], rows: unknown[][]) {
  let xKey = columns[0];
  let yKey = columns[1] ?? columns[0];
  for (const c of columns) {
    const sample = rows.find((r) => r[columns.indexOf(c)] !== null)?.[
      columns.indexOf(c)
    ];
    if (typeof sample === "number") {
      yKey = c;
      break;
    }
  }
  for (const c of columns) {
    const sample = rows.find((r) => r[columns.indexOf(c)] !== null)?.[
      columns.indexOf(c)
    ];
    if (typeof sample !== "number" && c !== yKey) {
      xKey = c;
      break;
    }
  }
  return { xKey, yKey };
}

interface ChartRendererProps {
  chartHint: ChartHint;
  columns: string[];
  rows: unknown[][];
}

export default function ChartRenderer({
  chartHint,
  columns,
  rows,
}: ChartRendererProps) {
  if (rows.length === 0) {
    return (
      <div className="px-6 py-12 text-center text-zinc-500 text-[13px]">
        Empty result — nothing to plot.
      </div>
    );
  }

  if (chartHint === "scalar") {
    const value = rows[0]?.[0];
    return (
      <div className="flex flex-col items-center justify-center px-6 py-16">
        <span className="eyebrow mb-6">{columns[0] ?? "result"}</span>
        <motion.div
          initial={{ opacity: 0, scale: 0.94 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          className="text-[88px] leading-none font-medium tracking-tight text-zinc-100
                     drop-shadow-[0_0_60px_rgba(197,245,0,0.18)]"
        >
          {typeof value === "number"
            ? value.toLocaleString(undefined, {
                maximumFractionDigits: 4,
              })
            : String(value ?? "—")}
        </motion.div>
        <div className="hr-soft w-24 mt-7" />
      </div>
    );
  }

  const data = toData(columns, rows);
  const { xKey, yKey } = pickAxes(columns, rows);

  if (chartHint === "bar") {
    return (
      <div className="px-3 pt-4 pb-2 h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 12, right: 16, left: 8, bottom: 24 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey={xKey}
              stroke="#52525b"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
              interval={0}
              angle={-25}
              textAnchor="end"
              height={70}
            />
            <YAxis
              stroke="#52525b"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              cursor={{ fill: "rgba(197,245,0,0.05)" }}
              contentStyle={TOOLTIP_STYLE}
              labelStyle={TOOLTIP_LABEL_STYLE}
              itemStyle={TOOLTIP_ITEM_STYLE}
            />
            <Bar
              dataKey={yKey}
              radius={[3, 3, 0, 0]}
              animationDuration={900}
              animationEasing="ease-out"
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (chartHint === "line") {
    return (
      <div className="px-3 pt-4 pb-2 h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 12, right: 16, left: 8, bottom: 24 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis
              dataKey={xKey}
              stroke="#52525b"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
              angle={-20}
              textAnchor="end"
              height={60}
            />
            <YAxis
              stroke="#52525b"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
            />
            <Tooltip
              cursor={{ stroke: "rgba(197,245,0,0.4)", strokeDasharray: 3 }}
              contentStyle={TOOLTIP_STYLE}
              labelStyle={TOOLTIP_LABEL_STYLE}
              itemStyle={TOOLTIP_ITEM_STYLE}
            />
            <Line
              type="monotone"
              dataKey={yKey}
              stroke="#c5f500"
              strokeWidth={2}
              dot={{ fill: "#c5f500", r: 3, strokeWidth: 0 }}
              activeDot={{ r: 5, fill: "#c5f500", strokeWidth: 2, stroke: "#09090b" }}
              animationDuration={1100}
              animationEasing="ease-out"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (chartHint === "pie") {
    return (
      <div className="px-3 pt-4 pb-2 h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              labelStyle={TOOLTIP_LABEL_STYLE}
              itemStyle={TOOLTIP_ITEM_STYLE}
            />
            <Pie
              data={data}
              dataKey={yKey}
              nameKey={xKey}
              cx="50%"
              cy="50%"
              outerRadius={140}
              innerRadius={70}
              paddingAngle={2}
              stroke="#09090b"
              strokeWidth={2}
              animationDuration={900}
              animationEasing="ease-out"
              label={({ name, percent }) =>
                `${name} · ${(percent! * 100).toFixed(0)}%`
              }
              labelLine={{ stroke: "rgba(255,255,255,0.2)" }}
            >
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div className="px-6 py-12 text-center text-zinc-500 text-[13px]">
      No chart for this shape — switch to the table view.
    </div>
  );
}

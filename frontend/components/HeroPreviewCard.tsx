"use client";

import { AnimatePresence, motion } from "motion/react";
import { Database, ShieldCheck, Sparkles } from "lucide-react";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

const CYCLE_MS = 9000;

type Demo = {
  pill: string;
  question: string;
  sql: ReactNode;
  resultLabel: string;
  result: ReactNode;
};

const DEMOS: Demo[] = [
  {
    pill: "bar",
    question: "Top 5 customers by number of orders.",
    sql: (
      <code>
        <span className="sql-kw">SELECT</span> c.CompanyName,
        {"\n       "}
        <span className="sql-fn">COUNT</span>(o.OrderID){" "}
        <span className="sql-kw">AS</span> orders{"\n"}
        <span className="sql-kw">FROM</span> Customers c{"\n"}
        <span className="sql-kw">JOIN</span> Orders o{"\n  "}
        <span className="sql-kw">ON</span> c.CustomerID = o.CustomerID
        {"\n"}
        <span className="sql-kw">GROUP BY</span> c.CustomerID{"\n"}
        <span className="sql-kw">ORDER BY</span> orders{" "}
        <span className="sql-kw">DESC</span>
        {"\n"}
        <span className="sql-kw">LIMIT</span>{" "}
        <span className="sql-str">5</span>;
      </code>
    ),
    resultLabel: "5 rows · bar",
    result: (
      <BarResult
        rows={[
          { label: "Save-a-lot Markets", value: 31, share: 1.0 },
          { label: "Ernst Handel", value: 30, share: 0.97 },
          { label: "QUICK-Stop", value: 28, share: 0.9 },
          { label: "Folk och fä HB", value: 19, share: 0.61 },
          { label: "Hungry Owl", value: 19, share: 0.61 },
        ]}
      />
    ),
  },
  {
    pill: "line",
    question: "Show monthly order count for the year 2017.",
    sql: (
      <code>
        <span className="sql-kw">SELECT</span>{" "}
        <span className="sql-fn">STRFTIME</span>(
        <span className="sql-str">'%Y-%m'</span>, OrderDate){" "}
        <span className="sql-kw">AS</span> month,
        {"\n       "}
        <span className="sql-fn">COUNT</span>(<span className="sql-pun">*</span>
        ) <span className="sql-kw">AS</span> orders{"\n"}
        <span className="sql-kw">FROM</span> Orders{"\n"}
        <span className="sql-kw">WHERE</span>{" "}
        <span className="sql-fn">STRFTIME</span>(
        <span className="sql-str">'%Y'</span>, OrderDate) ={" "}
        <span className="sql-str">'2017'</span>
        {"\n"}
        <span className="sql-kw">GROUP BY</span> month{"\n"}
        <span className="sql-kw">ORDER BY</span> month;
      </code>
    ),
    resultLabel: "12 rows · line",
    result: (
      <LineResult
        points={[55, 54, 73, 74, 56, 75, 71, 67, 70, 86, 78, 74]}
        labels={["Jan", "Apr", "Jul", "Oct"]}
      />
    ),
  },
  {
    pill: "scalar",
    question: "How many products are discontinued?",
    sql: (
      <code>
        <span className="sql-kw">SELECT</span>{" "}
        <span className="sql-fn">COUNT</span>(<span className="sql-pun">*</span>
        ) <span className="sql-kw">AS</span> discontinued
        {"\n"}
        <span className="sql-kw">FROM</span> Products{"\n"}
        <span className="sql-kw">WHERE</span> Discontinued ={" "}
        <span className="sql-str">1</span>;
      </code>
    ),
    resultLabel: "1 row · scalar",
    result: <ScalarResult value="8" unit="discontinued products" />,
  },
];

export default function HeroPreviewCard() {
  const [idx, setIdx] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(() => {
      setIdx((i) => (i + 1) % DEMOS.length);
    }, CYCLE_MS);
    return () => clearInterval(t);
  }, [paused]);

  const demo = DEMOS[idx];

  return (
    <div
      className="relative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* glow underlay */}
      <div
        className="absolute -inset-6 rounded-3xl pointer-events-none"
        style={{
          background:
            "radial-gradient(circle at 70% 30%, rgba(197,245,0,0.08), transparent 60%)",
          filter: "blur(40px)",
        }}
      />

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut", delay: 0.3 }}
        className="relative surface rounded-2xl p-1.5 shadow-[0_10px_40px_-12px_rgba(0,0,0,0.6)]
                   ring-1 ring-white/[0.05]"
      >
        <div className="rounded-xl bg-ink/60 p-5 sm:p-6 space-y-5">
          {/* fixed header bar — does not cycle */}
          <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-400">
            <span>Trace · /query · northwind</span>
            <div className="flex items-center gap-3">
              <PillRow active={idx} />
              <span className="text-success/80 inline-flex items-center gap-1.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inset-0 rounded-full bg-success opacity-50 animate-ping" />
                  <span className="relative h-1.5 w-1.5 rounded-full bg-success" />
                </span>
                live
              </span>
            </div>
          </div>

          <div className="hr-soft" />

          {/* cycling subtree — re-mounts on idx change so entrance animations replay */}
          <AnimatePresence mode="wait">
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="space-y-5"
            >
              {/* question */}
              <div className="relative pl-4 border-l-2 border-accent/60 space-y-1.5">
                <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-accent">
                  Asked
                </p>
                <p className="text-zinc-50 text-[16px] sm:text-[17px] leading-snug">
                  &ldquo;{demo.question}&rdquo;
                </p>
                <p className="text-[10px] font-mono uppercase tracking-[0.16em] text-zinc-400">
                  Database · northwind · 13 tables
                </p>
              </div>

              {/* mini pipeline — same for every cycle */}
              <PipelineMini />

              {/* SQL */}
              <div className="space-y-2">
                <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-400 inline-flex items-center gap-2">
                  <span className="text-accent">↳</span> Generated for the
                  question above
                </p>
                <motion.pre
                  initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }}
                  animate={{ opacity: 1, clipPath: "inset(0 0 0 0)" }}
                  transition={{
                    duration: 0.9,
                    ease: [0.65, 0.05, 0.36, 1],
                    delay: 0.15,
                  }}
                  className="font-mono text-[12px] sm:text-[12.5px] leading-relaxed
                             bg-zinc-950/60 rounded-lg p-3.5 border border-white/[0.05]
                             text-zinc-200 overflow-x-auto"
                >
                  {demo.sql}
                </motion.pre>
              </div>

              {/* result */}
              <div className="space-y-3 min-h-[170px]">
                <div className="flex items-center justify-between">
                  <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-400">
                    Result · {demo.resultLabel}
                  </p>
                  <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-500">
                    1 attempt
                  </p>
                </div>
                {demo.result}
              </div>
            </motion.div>
          </AnimatePresence>

          {/* progress bar — fills over the cycle, resets on advance */}
          <ProgressBar idx={idx} paused={paused} />
        </div>
      </motion.div>
    </div>
  );
}

/* ----- subviews ---------------------------------------------- */

function PipelineMini() {
  const stations = [
    { icon: Database, label: "Retrieve" },
    { icon: Sparkles, label: "Generate" },
    { icon: ShieldCheck, label: "Verify" },
  ];
  return (
    <div className="relative flex items-center justify-between gap-2">
      <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-px bg-white/[0.08]" />
      <div className="absolute left-4 right-4 top-1/2 -translate-y-1/2 h-px overflow-hidden">
        <span
          className="traveling-dot absolute -top-[3px] block h-[7px] w-[7px] rounded-full bg-accent"
          style={{ boxShadow: "0 0 12px rgba(197,245,0,0.8)" }}
        />
      </div>
      {stations.map(({ icon: Icon, label }, i) => (
        <div
          key={label}
          className="relative z-10 flex flex-col items-center gap-1.5"
        >
          <div
            className="station-pulse h-7 w-7 rounded-full bg-zinc-950 border border-accent/40 flex items-center justify-center"
            style={{ animationDelay: `${i * 0.6}s` }}
          >
            <Icon className="w-3 h-3 text-accent" strokeWidth={2} />
          </div>
          <span className="font-mono text-[9.5px] uppercase tracking-[0.16em] text-zinc-400">
            {label}
          </span>
        </div>
      ))}
    </div>
  );
}

function PillRow({ active }: { active: number }) {
  return (
    <div className="hidden sm:flex items-center gap-1">
      {DEMOS.map((d, i) => (
        <span
          key={d.pill}
          className={`px-1.5 py-[2px] rounded-md text-[9.5px] tracking-[0.16em] transition-colors duration-300 ${
            i === active
              ? "text-accent bg-accent/15 border border-accent/30"
              : "text-zinc-500 border border-white/[0.05]"
          }`}
        >
          {d.pill}
        </span>
      ))}
    </div>
  );
}

function ProgressBar({ idx, paused }: { idx: number; paused: boolean }) {
  return (
    <div className="flex gap-1.5 pt-2">
      {DEMOS.map((_, i) => (
        <div
          key={i}
          className="flex-1 h-[2px] rounded-full bg-white/[0.06] overflow-hidden"
        >
          {i === idx ? (
            <motion.div
              key={`active-${idx}-${paused ? "paused" : "running"}`}
              initial={{ width: "0%" }}
              animate={{ width: paused ? "0%" : "100%" }}
              transition={{
                duration: paused ? 0 : CYCLE_MS / 1000,
                ease: "linear",
              }}
              className="h-full bg-accent"
            />
          ) : i < idx ? (
            <div className="h-full w-full bg-accent/40" />
          ) : null}
        </div>
      ))}
    </div>
  );
}

function BarResult({
  rows,
}: {
  rows: { label: string; value: number; share: number }[];
}) {
  return (
    <div className="space-y-2.5">
      {rows.map((row, i) => (
        <div key={row.label} className="flex items-center gap-3">
          <span className="w-[120px] sm:w-[140px] truncate text-[12.5px] text-zinc-300 font-light">
            {row.label}
          </span>
          <div className="flex-1 h-[10px] bg-white/[0.04] rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${row.share * 100}%` }}
              transition={{
                duration: 0.7,
                ease: "easeOut",
                delay: 0.35 + i * 0.07,
              }}
              className="h-full bg-accent rounded-full"
              style={{ boxShadow: "0 0 12px -2px rgba(197,245,0,0.5)" }}
            />
          </div>
          <span className="w-7 text-right font-mono text-[11px] text-zinc-400">
            {row.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function LineResult({
  points,
  labels,
}: {
  points: number[];
  labels: string[];
}) {
  const dims = useMemo(() => {
    const w = 480;
    const h = 150;
    const pad = { l: 14, r: 14, t: 12, b: 22 };
    const innerW = w - pad.l - pad.r;
    const innerH = h - pad.t - pad.b;
    // Add 12% headroom top + bottom so peaks/troughs don't kiss the edges
    const rawMax = Math.max(...points);
    const rawMin = Math.min(...points);
    const rawSpan = rawMax - rawMin || 1;
    const max = rawMax + rawSpan * 0.12;
    const min = rawMin - rawSpan * 0.12;
    const span = max - min || 1;
    const coords = points.map((v, i) => {
      const x = pad.l + (i / (points.length - 1)) * innerW;
      const y = pad.t + (1 - (v - min) / span) * innerH;
      return [x, y] as const;
    });
    const linePath = "M " + coords.map(([x, y]) => `${x},${y}`).join(" L ");
    const areaPath = `${linePath} L ${coords[coords.length - 1][0]},${
      h - pad.b
    } L ${coords[0][0]},${h - pad.b} Z`;
    return { w, h, pad, innerW, innerH, coords, linePath, areaPath };
  }, [points]);

  return (
    <svg
      viewBox={`0 0 ${dims.w} ${dims.h}`}
      className="w-full h-[150px]"
      preserveAspectRatio="none"
    >
      {/* baseline */}
      <line
        x1={dims.pad.l}
        y1={dims.h - dims.pad.b}
        x2={dims.w - dims.pad.r}
        y2={dims.h - dims.pad.b}
        stroke="rgba(255,255,255,0.08)"
        strokeWidth="1"
      />
      {/* area */}
      <motion.path
        d={dims.areaPath}
        fill="rgba(197,245,0,0.10)"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.6, ease: "easeOut" }}
      />
      {/* line */}
      <motion.path
        d={dims.linePath}
        fill="none"
        stroke="rgb(197,245,0)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.4, ease: "easeOut", delay: 0.2 }}
        style={{ filter: "drop-shadow(0 0 6px rgba(197,245,0,0.5))" }}
      />
      {/* points */}
      {dims.coords.map(([x, y], i) => (
        <motion.circle
          key={i}
          cx={x}
          cy={y}
          r="2.5"
          fill="rgb(197,245,0)"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.25, delay: 0.5 + i * 0.05 }}
        />
      ))}
      {/* x labels */}
      {labels.map((m, i) => (
        <text
          key={m}
          x={dims.pad.l + (i / (labels.length - 1)) * dims.innerW}
          y={dims.h - 6}
          fontSize="9"
          fill="rgba(228,228,231,0.55)"
          fontFamily="ui-monospace, monospace"
          textAnchor="middle"
          letterSpacing="2"
        >
          {m.toUpperCase()}
        </text>
      ))}
    </svg>
  );
}

function ScalarResult({ value, unit }: { value: string; unit: string }) {
  // Animated count-up — drives a number from 0 to value
  const target = parseInt(value, 10) || 0;
  const [shown, setShown] = useState(0);
  const startedAt = useRef<number | null>(null);

  useEffect(() => {
    setShown(0);
    startedAt.current = null;
    let raf = 0;
    const dur = 900;
    const step = (ts: number) => {
      if (startedAt.current === null) startedAt.current = ts;
      const t = Math.min(1, (ts - startedAt.current) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(target * eased));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut", delay: 0.2 }}
      className="flex items-baseline gap-4 py-3"
    >
      <span className="numeral text-[88px] sm:text-[112px] text-zinc-50 leading-none">
        {shown}
      </span>
      <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
        {unit}
      </span>
    </motion.div>
  );
}

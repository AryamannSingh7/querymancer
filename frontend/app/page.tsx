import Link from "next/link";
import {
  ArrowUpRight,
  BarChart3,
  FileJson,
  Lock,
  Network,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

import HeroPreviewCard from "@/components/HeroPreviewCard";
import HeroQueryForm from "@/components/HeroQueryForm";
import LandingPipeline from "@/components/LandingPipeline";
import StatNumber from "@/components/StatNumber";
import { Mark } from "@/components/Ornament";

const HERO_CHIPS: { text: string }[] = [
  { text: "Top 5 customers by number of orders" },
  { text: "Show monthly order count for 2017" },
  { text: "Which categories have the most products?" },
  { text: "Employees who report to Andrew Fuller" },
];

const CAPS = [
  {
    icon: Network,
    title: "Schema RAG",
    body: "Every question is embedded with Gemini at 768 dimensions and matched against pgvector top-k. Only the relevant tables ever reach the prompt — the model never reads a 60-table catalog at once.",
  },
  {
    icon: FileJson,
    title: "Structured output",
    body: "Gemini 2.5 Flash returns JSON conforming to a strict response schema: SQL, an explanation, and a chart hint. No regex, no parsing surprises, no markdown to strip.",
  },
  {
    icon: ShieldCheck,
    title: "Safety gate",
    body: "sqlglot AST parsing rejects DDL/DML up front. A keyword denylist plus auto-LIMIT injection seal the rest. Single statement enforced. The DB opens read-only with a five-second timeout.",
  },
  {
    icon: RefreshCw,
    title: "Self-correction",
    body: "On execution failure, the verbatim SQLite error feeds back into the next prompt attempt. Up to three tries before the error surfaces — most failures resolve on attempt two.",
  },
  {
    icon: BarChart3,
    title: "Auto-charts",
    body: "The same structured response carries a chart hint: scalar, table, bar, line, or pie. The renderer picks animation, palette, and shape — no client-side guessing about the shape of the answer.",
  },
  {
    icon: Lock,
    title: "Read-only by contract",
    body: "Every connection opens with mode=ro at the file URI level. The safety pipeline is non-negotiable: AST + denylist + read-only mount. Two layers, not one.",
  },
];

const STATS: { num: number; suffix: string; unit: string; label: string }[] = [
  { num: 768, suffix: "", unit: "dims", label: "Gemini embeddings" },
  { num: 5, suffix: "", unit: "top-k", label: "Schema chunks per question" },
  { num: 3, suffix: "", unit: "tries", label: "Self-correction budget" },
  { num: 5, suffix: "s", unit: "max", label: "Read-only query timeout" },
];

const STACK = [
  "Next.js 16",
  "FastAPI",
  "Gemini 2.5 Flash",
  "pgvector",
  "Supabase",
  "SQLite",
  "sqlglot",
  "Tailwind v4",
  "motion/react",
  "Recharts",
];

// CSS animation-delay (ms) per hero element — lets the page choreograph an entrance
const HERO_DELAYS = {
  eyebrow: 50,
  h1: 140,
  sub: 380,
  form: 560,
  chips: 740,
  meta: 900,
  card: 220,
} as const;

export default function Page() {
  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      {/* layered backdrop */}
      <div className="bg-glow-landing" aria-hidden />
      <div
        className="absolute inset-0 bg-dotgrid pointer-events-none opacity-70"
        aria-hidden
      />
      <div
        className="absolute inset-x-0 top-0 h-[420px] pointer-events-none"
        aria-hidden
        style={{
          background:
            "linear-gradient(180deg, rgba(9,9,11,0) 0%, rgba(9,9,11,0.85) 70%, rgba(9,9,11,1) 100%)",
        }}
      />

      <SiteHeader />

      <div className="relative z-10 mx-auto max-w-6xl px-6 sm:px-10">
        {/* HERO */}
        <section className="pt-10 sm:pt-16 pb-20 sm:pb-28">
          <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,520px)] gap-12 lg:gap-14 items-start">
            <div>
              <p
                className="eyebrow-accent rise"
                style={{ animationDelay: `${HERO_DELAYS.eyebrow}ms` }}
              >
                Phase V · Live demo · Read-only
              </p>

              <h1
                className="mt-6 font-display font-extralight leading-[0.95] tracking-tight text-zinc-50
                           text-[44px] sm:text-6xl md:text-[76px] rise"
                style={{ animationDelay: `${HERO_DELAYS.h1}ms` }}
              >
                Ask your database
                <br />
                in{" "}
                <span className="relative inline-block italic font-light text-accent">
                  plain
                  <span
                    className="absolute -bottom-1 left-0 right-0 h-[2px] bg-accent/60 accent-sweep"
                    style={{ animationDelay: `${HERO_DELAYS.h1 + 600}ms` }}
                  />
                </span>{" "}
                English.
              </h1>

              <p
                className="mt-7 max-w-2xl text-zinc-300 leading-relaxed
                           text-[17px] sm:text-[19px] rise"
                style={{ animationDelay: `${HERO_DELAYS.sub}ms` }}
              >
                Querymancer retrieves the relevant schema with vector search,
                generates SQL through a strict structured-output contract, runs
                it read-only against bundled SQLite databases, and renders the
                answer — table, bar, line, or pie. Three attempts of
                self-correction on failure.
              </p>

              <div
                className="mt-9 rise"
                style={{ animationDelay: `${HERO_DELAYS.form}ms` }}
              >
                <HeroQueryForm />
              </div>

              <div
                className="mt-6 flex flex-wrap items-center gap-2 rise"
                style={{ animationDelay: `${HERO_DELAYS.chips}ms` }}
              >
                <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-400 mr-2">
                  Try
                </span>
                {HERO_CHIPS.map((chip) => (
                  <Link
                    key={chip.text}
                    href={`/app?q=${encodeURIComponent(chip.text)}`}
                    className="px-3 py-1.5 rounded-full surface-2 row-hover
                               text-[12px] sm:text-[13px] text-zinc-100
                               transition-transform hover:-translate-y-0.5"
                  >
                    {chip.text}
                  </Link>
                ))}
              </div>

              {/* meta strip */}
              <div
                className="mt-12 flex flex-wrap gap-x-8 gap-y-4 text-[11px] font-mono uppercase tracking-[0.18em] rise"
                style={{ animationDelay: `${HERO_DELAYS.meta}ms` }}
              >
                <MetaItem label="Backend" value="FastAPI" />
                <MetaItem label="LLM" value="Gemini 2.5 Flash" />
                <MetaItem label="Vector store" value="Supabase pgvector" />
                <MetaItem label="DBs bundled" value="3 SQLite" />
              </div>
            </div>

            {/* preview card */}
            <div
              className="rise"
              style={{ animationDelay: `${HERO_DELAYS.card}ms` }}
            >
              <HeroPreviewCard />
            </div>
          </div>
        </section>

        {/* PIPELINE */}
        <LandingPipeline />

        {/* CAPABILITIES */}
        <section className="py-20 sm:py-24 border-t border-white/[0.06]">
          <div className="grid gap-10 md:grid-cols-[260px_1fr] md:gap-16">
            <div>
              <p className="eyebrow-accent">Under the hood</p>
              <h2 className="mt-4 font-display font-extralight tracking-tight text-zinc-50
                             text-[28px] sm:text-[40px] leading-[1.05]">
                Six layers,
                <br />
                <span className="text-zinc-400">all enforced.</span>
              </h2>
              <p className="mt-6 text-zinc-300 text-[15px] leading-relaxed">
                The agent loop is small on purpose. Most of the work lives in
                the contracts that surround it.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              {CAPS.map(({ icon: Icon, title, body }, i) => (
                <div
                  key={title}
                  className="cap-card p-5 sm:p-6 rise"
                  style={{ animationDelay: `${120 + i * 70}ms` }}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-9 w-9 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-accent" strokeWidth={1.7} />
                    </div>
                    <h3 className="font-display text-[19px] font-light tracking-tight text-zinc-50">
                      {title}
                    </h3>
                  </div>
                  <p className="text-zinc-300 text-[13.5px] leading-relaxed">
                    {body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* STATS */}
        <section className="py-16 sm:py-20 border-t border-white/[0.06]">
          <p className="eyebrow mb-8 sm:mb-12">By the numbers</p>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {STATS.map((s) => (
              <div key={s.label} className="space-y-3">
                <div className="flex items-baseline gap-2">
                  <StatNumber
                    value={s.num}
                    suffix={s.suffix}
                    className="numeral text-[56px] sm:text-[72px] text-zinc-50"
                  />
                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
                    {s.unit}
                  </span>
                </div>
                <p className="text-zinc-300 text-[13.5px] leading-snug max-w-[180px]">
                  {s.label}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 sm:py-28">
          <div className="relative overflow-hidden rounded-3xl surface p-8 sm:p-14
                          ring-1 ring-white/[0.06]">
            <div
              className="absolute -top-32 -right-32 w-[520px] h-[520px] pointer-events-none"
              style={{
                background:
                  "radial-gradient(closest-side, rgba(197,245,0,0.16), transparent 70%)",
                filter: "blur(40px)",
              }}
              aria-hidden
            />
            <div className="relative grid gap-8 md:grid-cols-[1fr_auto] md:items-end">
              <div>
                <p className="eyebrow-accent">Ready</p>
                <h2 className="mt-4 font-display font-extralight tracking-tight text-zinc-50
                               text-[34px] sm:text-[52px] leading-[1.02]">
                  Open a database.
                  <br />
                  <span className="text-zinc-400">Ask a question.</span>
                </h2>
                <p className="mt-5 max-w-xl text-zinc-300 text-[15px] sm:text-[16px] leading-relaxed">
                  The full demo is one click away. Three sample databases,
                  curated questions to try, and the same safety pipeline used
                  in the trace card above.
                </p>
              </div>

              <Link
                href="/app"
                className="group relative inline-flex items-center gap-3 self-end
                           bg-accent hover:bg-accent-soft text-ink
                           px-7 py-4 rounded-2xl
                           font-mono text-[13px] uppercase tracking-[0.18em] font-medium
                           shadow-[0_0_40px_-8px_rgba(197,245,0,0.6)]
                           hover:shadow-[0_0_60px_-6px_rgba(197,245,0,0.85)]
                           transition-all hover:-translate-y-0.5"
              >
                Launch Querymancer
                <ArrowUpRight
                  className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                  strokeWidth={2}
                />
              </Link>
            </div>
          </div>
        </section>

        {/* STACK STRIP — pills */}
        <section className="py-12 border-t border-white/[0.06]">
          <div className="flex flex-col sm:flex-row sm:items-center gap-5 sm:gap-10">
            <p className="eyebrow shrink-0">Built with</p>
            <ul className="flex flex-wrap gap-2">
              {STACK.map((name) => (
                <li
                  key={name}
                  className="px-3 py-1 rounded-full text-[12px] font-mono
                             text-zinc-200 bg-white/[0.03] border border-white/[0.06]
                             hover:border-accent/30 hover:bg-accent/[0.04] hover:text-accent
                             transition-colors"
                >
                  {name}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <SiteFooter />
      </div>
    </div>
  );
}

function SiteHeader() {
  return (
    <header
      className="sticky top-0 z-30 backdrop-blur-xl bg-ink/70
                 border-b border-white/[0.06]"
    >
      <div className="mx-auto max-w-6xl px-6 sm:px-10 flex items-center justify-between py-5 sm:py-6">
        <Link
          href="/"
          className="flex items-center gap-3 group"
          aria-label="Querymancer home"
        >
          <Mark className="w-6 h-6 text-accent transition-transform group-hover:scale-110" />
          <div className="leading-tight">
            <span className="block text-zinc-50 text-[15px] font-medium tracking-tight">
              Querymancer
            </span>
            <span className="block text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-400 mt-0.5">
              natural language → sql
            </span>
          </div>
        </Link>

        <nav className="flex items-center gap-5 sm:gap-7 text-[11px] font-mono uppercase tracking-[0.18em]">
          <a
            href="https://github.com/AryamannSingh7/querymancer"
            target="_blank"
            rel="noreferrer"
            className="text-zinc-300 hover:text-zinc-50 transition-colors inline-flex items-center gap-1"
          >
            GitHub
            <ArrowUpRight className="w-3 h-3" strokeWidth={2} />
          </a>
          <Link
            href="/app"
            className="text-zinc-50 hover:text-accent transition-colors"
          >
            Launch app →
          </Link>
        </nav>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-white/[0.06] py-8 mt-8 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-400">
      <span>v0.5 · Phase V · Multi-turn + polish</span>
      <span>
        Built by{" "}
        <a
          href="https://github.com/AryamannSingh7"
          target="_blank"
          rel="noreferrer"
          className="text-zinc-100 hover:text-accent transition-colors normal-case tracking-normal font-sans"
        >
          Aryamann Singh
        </a>
      </span>
    </footer>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-zinc-400">{label}</span>
      <span className="text-zinc-100 normal-case tracking-tight font-sans text-[13px]">
        {value}
      </span>
    </div>
  );
}

"use client";

import { motion } from "motion/react";
import {
  Database,
  Network,
  Sparkles,
  ShieldCheck,
  BarChart3,
  type LucideIcon,
} from "lucide-react";

type Station = {
  n: string;
  label: string;
  sub: string;
  icon: LucideIcon;
};

const STATIONS: Station[] = [
  { n: "01", label: "Embed", sub: "768-d Gemini", icon: Network },
  { n: "02", label: "Retrieve", sub: "pgvector top-k", icon: Database },
  { n: "03", label: "Generate", sub: "Flash · structured", icon: Sparkles },
  { n: "04", label: "Verify", sub: "AST · denylist · ro", icon: ShieldCheck },
  { n: "05", label: "Render", sub: "table · bar · line", icon: BarChart3 },
];

export default function LandingPipeline() {
  return (
    <section className="py-16 sm:py-24 border-t border-white/[0.06] relative">
      <div className="mb-12 max-w-2xl">
        <p className="eyebrow-accent">The pipeline</p>
        <h2 className="mt-4 font-display font-extralight tracking-tight text-zinc-50
                       text-[28px] sm:text-[40px] leading-[1.05]">
          Five stations from{" "}
          <span className="text-zinc-400">question</span> to{" "}
          <span className="text-accent italic">answer.</span>
        </h2>
      </div>

      {/* horizontal pipeline — desktop */}
      <div className="hidden md:block relative">
        {/* track */}
        <div className="absolute left-0 right-0 top-[34px] h-px bg-white/[0.07]" />
        {/* traveling dot */}
        <div className="absolute left-0 right-0 top-[31px] h-[7px] overflow-hidden pointer-events-none">
          <span
            className="traveling-dot absolute -top-[1px] block h-[7px] w-[7px] rounded-full bg-accent"
            style={{ boxShadow: "0 0 14px rgba(197,245,0,0.9)" }}
          />
        </div>

        <div className="relative grid grid-cols-5 gap-4">
          {STATIONS.map((s, i) => (
            <motion.div
              key={s.n}
              initial={{ opacity: 0, y: 8 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.5, delay: i * 0.08, ease: "easeOut" }}
              className="flex flex-col items-center text-center"
            >
              <div
                className="station-pulse h-[68px] w-[68px] rounded-2xl bg-ink
                           border border-accent/30 flex items-center justify-center
                           relative z-10"
                style={{ animationDelay: `${i * 0.5}s` }}
              >
                <s.icon className="w-6 h-6 text-accent" strokeWidth={1.5} />
              </div>
              <span className="mt-5 font-mono text-[10px] tracking-[0.18em] uppercase text-zinc-500">
                {s.n}
              </span>
              <span className="mt-1 font-display text-[18px] font-light tracking-tight text-zinc-100">
                {s.label}
              </span>
              <span className="mt-1 font-mono text-[10.5px] uppercase tracking-[0.14em] text-zinc-400">
                {s.sub}
              </span>
            </motion.div>
          ))}
        </div>
      </div>

      {/* vertical pipeline — mobile */}
      <div className="md:hidden relative pl-10">
        <div className="absolute left-[18px] top-2 bottom-2 w-px bg-white/[0.07]" />
        <div className="absolute left-[14px] top-2 bottom-2 w-[9px] overflow-hidden pointer-events-none">
          <span
            className="absolute left-1/2 -translate-x-1/2 block h-[7px] w-[7px] rounded-full bg-accent"
            style={{
              animation: "traverseY 4s cubic-bezier(0.5,0,0.5,1) infinite",
              boxShadow: "0 0 12px rgba(197,245,0,0.8)",
            }}
          />
        </div>
        <div className="space-y-7">
          {STATIONS.map((s) => (
            <div key={s.n} className="flex items-start gap-5 relative">
              <div className="-ml-10 station-pulse h-9 w-9 rounded-xl bg-inkborder border-accent/30 flex items-center justify-center shrink-0 relative z-10">
                <s.icon className="w-4 h-4 text-accent" strokeWidth={1.5} />
              </div>
              <div className="flex-1">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-zinc-500">
                    {s.n}
                  </span>
                  <span className="font-display text-[18px] font-light tracking-tight text-zinc-100">
                    {s.label}
                  </span>
                </div>
                <span className="block mt-0.5 font-mono text-[10.5px] uppercase tracking-[0.14em] text-zinc-400">
                  {s.sub}
                </span>
              </div>
            </div>
          ))}
        </div>
        <style>{`
          @keyframes traverseY {
            0% { top: 0; opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { top: 100%; opacity: 0; }
          }
        `}</style>
      </div>
    </section>
  );
}

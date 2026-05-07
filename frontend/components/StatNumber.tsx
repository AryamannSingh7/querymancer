"use client";

import { useInView } from "motion/react";
import { useEffect, useRef, useState } from "react";

type Props = {
  value: number;
  suffix?: string;
  durationMs?: number;
  className?: string;
};

export default function StatNumber({
  value,
  suffix = "",
  durationMs = 1100,
  className,
}: Props) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  const [shown, setShown] = useState(0);

  useEffect(() => {
    if (!inView) return;
    let raf = 0;
    let started: number | null = null;
    const step = (ts: number) => {
      if (started === null) started = ts;
      const t = Math.min(1, (ts - started) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setShown(Math.round(value * eased));
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView, value, durationMs]);

  return (
    <span ref={ref} className={className}>
      {shown}
      {suffix}
    </span>
  );
}

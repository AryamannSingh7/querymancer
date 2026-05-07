"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";

/**
 * Custom syntax theme for the SQL block — matches the Console palette.
 * Lime accent on keywords, zinc text otherwise. No off-the-shelf theme.
 */
const consoleStyle: { [key: string]: React.CSSProperties } = {
  'pre[class*="language-"]': {
    background: "transparent",
    margin: 0,
    padding: 0,
    fontFamily: "var(--font-mono)",
    fontSize: "13px",
    lineHeight: "1.7",
    color: "#e4e4e7",
    textShadow: "none",
  },
  'code[class*="language-"]': {
    background: "transparent",
    fontFamily: "var(--font-mono)",
    color: "#e4e4e7",
    textShadow: "none",
  },
  keyword: { color: "#c5f500", fontWeight: 500 },
  function: { color: "#a1a1aa" },
  number: { color: "#e2fa7a" },
  string: { color: "#fb923c" },
  operator: { color: "#a1a1aa" },
  punctuation: { color: "#71717a" },
  comment: { color: "#52525b", fontStyle: "italic" },
  boolean: { color: "#4ade80" },
};

interface SqlBlockProps {
  sql: string;
  animateIn?: boolean;
}

export default function SqlBlock({ sql, animateIn = true }: SqlBlockProps) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <figure className="relative surface rounded-lg overflow-hidden">
      <header className="flex items-center justify-between px-4 py-2 border-b border-white/[0.06] bg-ink/40">
        <span className="eyebrow-accent">sql</span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1.5 text-[10px] font-mono tracking-[0.2em] uppercase
                     text-zinc-500 hover:text-accent transition-colors"
          aria-label="Copy SQL"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" strokeWidth={1.5} />
              copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" strokeWidth={1.5} />
              copy
            </>
          )}
        </button>
      </header>

      <div className={`p-4 overflow-x-auto ${animateIn ? "scribe-in" : ""}`}>
        <SyntaxHighlighter
          language="sql"
          style={consoleStyle}
          PreTag="div"
          wrapLongLines
        >
          {sql}
        </SyntaxHighlighter>
      </div>
    </figure>
  );
}

import type { Metadata } from "next";
import { Bricolage_Grotesque, Geist_Mono } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
  subsets: ["latin"],
  weight: ["200", "300", "400", "500", "600", "700", "800"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  // Resolves relative OG/Twitter image URLs against this base. Override
  // via NEXT_PUBLIC_SITE_URL when deploying (Vercel) — defaults to the
  // local dev origin so the build doesn't warn during development.
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  ),
  title: {
    default: "Querymancer · Natural language to SQL",
    template: "%s · Querymancer",
  },
  description:
    "Ask your database in plain English. Querymancer retrieves the relevant schema, generates SQL with Gemini, runs it read-only, and renders the answer.",
  applicationName: "Querymancer",
  authors: [{ name: "Aryamann Singh" }],
  keywords: [
    "natural language to SQL",
    "text-to-SQL",
    "Gemini",
    "RAG",
    "schema embeddings",
    "FastAPI",
    "Next.js",
  ],
  // og:image and twitter:image are picked up from app/opengraph-image.tsx
  // automatically. We still set type / locale / siteName here.
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "Querymancer",
    title: "Querymancer · Natural language to SQL",
    description:
      "Ask your database in plain English. Schema RAG + Gemini + a safety-gated SQLite executor.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Querymancer · Natural language to SQL",
    description:
      "Ask your database in plain English. Schema RAG + Gemini + a safety-gated SQLite executor.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${bricolage.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full">{children}</body>
    </html>
  );
}

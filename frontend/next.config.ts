import type { NextConfig } from "next";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /**
   * Same-origin proxy to the FastAPI backend.
   * Avoids browser CORS / Private Network Access on dev. The frontend
   * calls /backend/query (same origin), Next rewrites server-side to
   * the real backend URL.
   */
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;

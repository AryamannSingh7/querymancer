import type {
  AgentExhaustedDetail,
  QueryRequest,
  QueryResponse,
  SchemaTable,
} from "./types";

// Same-origin path. next.config.ts rewrites /backend/* to the FastAPI host.
// Avoids browser CORS / Private Network Access entirely.
const BACKEND_URL = "/backend";

export class AgentExhaustedError extends Error {
  detail: AgentExhaustedDetail;
  constructor(detail: AgentExhaustedDetail) {
    super(detail.message);
    this.name = "AgentExhaustedError";
    this.detail = detail;
  }
}

export class UnknownDatabaseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UnknownDatabaseError";
  }
}

export class UpstreamError extends Error {
  detail: AgentExhaustedDetail;
  constructor(detail: AgentExhaustedDetail) {
    super(detail.message);
    this.name = "UpstreamError";
    this.detail = detail;
  }
}

export async function postQuery(req: QueryRequest): Promise<QueryResponse> {
  const res = await fetch(`${BACKEND_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (res.status === 200) {
    return (await res.json()) as QueryResponse;
  }

  // FastAPI puts the structured detail under `detail`
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;

  if (res.status === 400 && typeof body?.detail === "string") {
    throw new UnknownDatabaseError(body.detail);
  }

  if (res.status === 422 && body?.detail && typeof body.detail === "object") {
    const detail = body.detail as AgentExhaustedDetail;
    if (typeof detail.message === "string") {
      throw new AgentExhaustedError(detail);
    }
  }

  // 429 (per-IP limiter) / 502 / 503 — all carry the structured detail
  // shape and all map to the clean "try again" UX.
  if (
    (res.status === 429 || res.status === 502 || res.status === 503) &&
    body?.detail &&
    typeof body.detail === "object"
  ) {
    const detail = body.detail as AgentExhaustedDetail;
    if (typeof detail.message === "string") {
      throw new UpstreamError(detail);
    }
  }

  throw new Error(
    `Query failed: ${res.status} ${res.statusText}` +
      (body ? ` — ${JSON.stringify(body)}` : ""),
  );
}

export async function getSchema(databaseId: string): Promise<SchemaTable[]> {
  const res = await fetch(`${BACKEND_URL}/databases/${databaseId}/schema`);
  if (!res.ok) {
    throw new Error(`Schema fetch failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SchemaTable[];
}

// ---- Streaming variant (Phase 5: live "self-correcting…" UX) ----

export interface StreamCallbacks {
  onAttemptStart: (attempt: number) => void;
  onAttemptFail: (attempt: number, reason: string) => void;
}

/**
 * POST /query/stream — consumes NDJSON events as the self-correction
 * loop runs and resolves to the final QueryResponse. Throws the same
 * error classes as `postQuery` so callers can keep their existing
 * error-handling branches.
 */
export async function postQueryStream(
  req: QueryRequest,
  callbacks: StreamCallbacks,
): Promise<QueryResponse> {
  const res = await fetch(`${BACKEND_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  // The per-IP limiter rejects before the stream starts — a plain 429 JSON
  // body, never an NDJSON stream. Surface it as the clean "try again" UX.
  if (res.status === 429) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    const detail = body?.detail;
    if (detail && typeof detail === "object") {
      throw new UpstreamError(detail as AgentExhaustedDetail);
    }
    throw new UpstreamError({
      message: "The demo is rate-limited right now. Wait a minute and try again.",
      attempts: 0,
      errors: [],
    });
  }

  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status} ${res.statusText}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: QueryResponse | null = null;
  let pendingError: Error | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const raw of lines) {
      const line = raw.trim();
      if (!line) continue;
      let event: Record<string, unknown>;
      try {
        event = JSON.parse(line);
      } catch {
        continue;
      }
      switch (event.event) {
        case "attempt_started":
          callbacks.onAttemptStart(event.attempt as number);
          break;
        case "attempt_failed":
          callbacks.onAttemptFail(
            event.attempt as number,
            (event.reason as string) ?? "",
          );
          break;
        case "result":
          finalResult = {
            sql: event.sql as string,
            explanation: event.explanation as string,
            chart_hint: event.chart_hint as QueryResponse["chart_hint"],
            columns: event.columns as string[],
            rows: event.rows as unknown[][],
            attempts: event.attempts as number,
            session_id: event.session_id as string,
          };
          break;
        case "error": {
          const message = (event.message as string) ?? "stream error";
          const kind = event.kind as string;
          if (kind === "agent_exhausted") {
            pendingError = new AgentExhaustedError({
              message,
              attempts: (event.attempts as number) ?? 0,
              errors: (event.errors as string[]) ?? [],
            });
          } else if (kind === "unknown_database") {
            pendingError = new UnknownDatabaseError(message);
          } else if (
            kind === "upstream_rate_limit" ||
            kind === "upstream_error" ||
            kind === "upstream_unavailable"
          ) {
            pendingError = new UpstreamError({
              message,
              attempts: 0,
              errors: (event.errors as string[]) ?? [],
            });
          } else {
            pendingError = new Error(message);
          }
          break;
        }
      }
    }
  }

  if (pendingError) throw pendingError;
  if (!finalResult) throw new Error("stream ended without a result event");
  return finalResult;
}

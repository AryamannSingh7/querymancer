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

  // 502/503 — Gemini upstream issues (rate-limit or transient outage)
  if (
    (res.status === 502 || res.status === 503) &&
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

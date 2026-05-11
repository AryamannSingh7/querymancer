// Mirrors backend/app/models.py — keep in sync if the backend contract changes.

export type ChartHint = "table" | "bar" | "line" | "pie" | "scalar";

export interface QueryRequest {
  question: string;
  database_id: string;
  // Omit on the first turn; the server returns one. Pass it back on
  // every follow-up so the backend can inline last 2 turns into the prompt.
  session_id?: string;
}

export interface QueryResponse {
  sql: string;
  explanation: string;
  chart_hint: ChartHint;
  columns: string[];
  rows: unknown[][];
  attempts: number;
  session_id: string;
}

// Shape of the 422 detail body when the agent exhausts all retries
export interface AgentExhaustedDetail {
  message: string;
  attempts: number;
  errors: string[];
}

// Mirrors backend/app/core/introspect.py
export interface SchemaColumn {
  name: string;
  type: string;
  notnull: boolean;
  pk: boolean;
}

export interface SchemaForeignKey {
  from_col: string;
  to_table: string;
  to_col: string;
}

export interface SchemaTable {
  name: string;
  row_count: number;
  columns: SchemaColumn[];
  foreign_keys: SchemaForeignKey[];
  referenced_by: SchemaForeignKey[];
}

export type Turn =
  | {
      id: string;
      kind: "pending";
      question: string;
      // Set by the /query/stream consumer as attempt events arrive.
      // Drives the "self-correcting… attempt N of 3" indicator.
      currentAttempt?: number;
      lastReason?: string;
    }
  | {
      id: string;
      kind: "success";
      question: string;
      response: QueryResponse;
    }
  | {
      id: string;
      kind: "exhausted";
      question: string;
      detail: AgentExhaustedDetail;
    }
  | {
      id: string;
      kind: "error";
      question: string;
      error: string;
    };

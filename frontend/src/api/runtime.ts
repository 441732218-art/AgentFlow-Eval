import { apiClient } from "./client";

export type ExecutionSummary = {
  execution_id: string;
  agent_id?: string;
  status: string;
  started_at?: string;
  completed_at?: string | null;
  duration?: number | null;
  duration_ms?: number | null;
  result?: unknown;
  error?: string | null;
  trace_available?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type ExecutionListResponse = {
  items: ExecutionSummary[];
  total?: number;
  limit?: number;
  offset?: number;
  next_cursor?: string | null;
  has_more?: boolean;
};

export type ListExecutionsParams = {
  agent_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
};

/** Runtime observability API — read-only execution discovery and detail. */
export const runtimeApi = {
  listExecutions: (params: ListExecutionsParams = {}) =>
    apiClient
      .get<ExecutionListResponse>("/runtime/executions", { params })
      .then((r) => r.data),

  getExecution: (executionId: string) =>
    apiClient.get<ExecutionSummary>(`/runtime/executions/${executionId}`).then((r) => r.data),
};

/* (c) 2026 AgentFlow-Eval */
import { apiClient } from "../client";

export type BusinessKpis = {
  window_days: number;
  since?: string;
  tasks_total: number;
  by_status: Record<string, number>;
  success_rate: number | null;
  avg_metric_score: number | null;
  total_tokens: number;
  avg_trace_latency_ms: number | null;
  error_topology: Record<string, number>;
};

export type KpisResponse = {
  enabled: boolean;
  kpis: BusinessKpis;
  deploy?: Record<string, unknown>;
};

export type SlowTaskItem = {
  stage: string;
  duration_sec: number;
  threshold_sec: number;
  ref_id?: string | null;
  status?: string;
  at?: number;
  trace_id?: string | null;
  extra?: Record<string, unknown>;
};

export const observabilityApi = {
  kpis: (days = 7) =>
    apiClient
      .get<KpisResponse>("/observability/kpis", { params: { days } })
      .then((r) => r.data),
  slowTasks: (limit = 20, source: "auto" | "db" | "memory" = "auto") =>
    apiClient
      .get<{
        items: SlowTaskItem[];
        total: number;
        threshold_sec: number;
        source?: string;
      }>("/observability/slow-tasks", { params: { limit, source } })
      .then((r) => r.data),
  errorTopology: (days = 7) =>
    apiClient
      .get<{ topology: Record<string, number>; by_status: Record<string, number> }>(
        "/observability/error-topology",
        { params: { days } }
      )
      .then((r) => r.data),
};

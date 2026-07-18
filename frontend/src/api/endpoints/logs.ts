/* (c) 2026 AgentFlow-Eval — AOLS log query API */
import { apiClient } from "../client";

export type AgentLogItem = {
  id: string;
  level: string;
  event: string;
  service: string;
  trace_id?: string | null;
  task_id?: string | null;
  payload: Record<string, unknown>;
  created_at?: string | null;
};

export type LogsListResponse = {
  items: AgentLogItem[];
  total: number;
  page: number;
  page_size: number;
};

export type LogsStatistics = {
  window_days: number;
  since?: string;
  error_count: number;
  total_events: number;
  agent_failure_rate: number | null;
  agent_failed: number;
  agent_completed: number;
  by_event: Record<string, number>;
  token_trend: Array<{ t: string; v: number }>;
  latency_trend: Array<{ t: string; v: number }>;
  error_trend: Array<{ t: string; v: number }>;
};

export type LogsListParams = {
  page?: number;
  page_size?: number;
  level?: string;
  event?: string;
  task_id?: string;
  trace_id?: string;
  since?: string;
  until?: string;
};

export const logsApi = {
  list: (params?: LogsListParams) =>
    apiClient
      .get<LogsListResponse>("/logs", { params })
      .then((r) => r.data),

  statistics: (days = 7) =>
    apiClient
      .get<LogsStatistics>("/logs/statistics", { params: { days } })
      .then((r) => r.data),
};

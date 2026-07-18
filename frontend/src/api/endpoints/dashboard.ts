/* (c) 2026 AgentFlow-Eval */
import { apiClient } from "../client";

export interface DashboardStats {
  actor: string;
  tasks_total: number;
  tasks_by_status: Record<string, number>;
  suites_total: number;
  active_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
}

export type DashboardSeriesPoint = { t: string; v: number };

export type NamedValue = { name: string; value: number };

export type DashboardOverview = {
  health: number;
  agents: number;
  success_rate: number | null;
  failure_rate: number | null;
  latency: number | null;
  latency_ms: number | null;
  tokens: number;
  cost: number | null;
  avg_score: number | null;
  stats: DashboardStats;
  kpis: Record<string, unknown>;
  series: {
    agents: DashboardSeriesPoint[];
    tokens: DashboardSeriesPoint[];
    latency: DashboardSeriesPoint[];
    errors: DashboardSeriesPoint[];
    success_rate?: DashboardSeriesPoint[];
  };
  series_meta?: {
    source?: string;
    days?: number;
  };
  status_distribution?: NamedValue[];
  error_topology?: NamedValue[];
  topology: {
    layout?: "horizontal" | "vertical";
    nodes: Array<{
      id: string;
      label: string;
      status?: string;
      kind?: string;
      meta?: Record<string, unknown>;
    }>;
    edges: Array<{
      source: string;
      target: string;
      type?: string;
      label?: string;
    }>;
    legend?: Array<{ status: string; label: string }>;
  };
  window_days: number;
};

export const dashboardApi = {
  stats: () =>
    apiClient.get<DashboardStats>("/dashboard/stats").then((r) => r.data),

  overview: (days = 7) =>
    apiClient
      .get<DashboardOverview>("/dashboard", { params: { days } })
      .then((r) => r.data),
};

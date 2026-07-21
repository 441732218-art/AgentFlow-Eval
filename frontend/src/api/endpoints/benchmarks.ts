/* (c) 2026 AgentFlow-Eval — Continuous Evaluation (Phase 4) */
import { apiClient } from "../client";

export type BenchmarkCase = {
  id?: string;
  name?: string;
  user_query: string;
  expected_output?: string;
  expected_tools?: string[];
  weight?: number;
};

export type Benchmark = {
  id: string;
  name: string;
  description?: string;
  status?: string;
  created_by?: string;
  tags?: string[];
  version?: string;
  scorecard?: Record<string, unknown> | null;
  source_task_id?: string | null;
  case_count?: number | null;
  cases?: BenchmarkCase[];
  created_at?: string | null;
};

export type BenchmarkRun = {
  id: string;
  benchmark_id: string;
  task_id?: string | null;
  label: string;
  status: string;
  agent_config?: Record<string, unknown>;
  summary?: {
    score?: number | null;
    accuracy?: number | null;
    quality?: number | null;
    success_rate?: number | null;
    score_coverage?: number | null;
    dimension_scores?: Record<string, number | null>;
    case_count?: number;
    latency_ms?: number | null;
    tokens?: number | null;
    cost?: number | null;
    [key: string]: unknown;
  };
  created_by?: string;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
};

export type LeaderboardRow = {
  rank: number;
  label: string;
  run_id: string;
  task_id?: string | null;
  status: string;
  accuracy?: number | null;
  quality?: number | null;
  latency_ms?: number | null;
  cost?: number | null;
  tokens?: number | null;
  score?: number | null;
  agent_config?: Record<string, unknown>;
  runs_count?: number;
};

/** Continuous eval: current vs baseline comparison payload */
export type RunComparison = {
  benchmark_id: string;
  verdict: "improved" | "stable" | "regressed" | "unknown";
  headline: string;
  score_delta: number | null;
  success_rate_delta: number | null;
  score_coverage_delta: number | null;
  dimension_deltas: Record<string, number | null>;
  top_changes: Array<{ dimension: string; delta: number }>;
  current: {
    run_id: string;
    label: string;
    task_id?: string | null;
    status: string;
    summary: Record<string, unknown>;
    created_at?: string | null;
  };
  baseline: {
    run_id: string;
    label: string;
    task_id?: string | null;
    status: string;
    summary: Record<string, unknown>;
    created_at?: string | null;
  };
  thresholds?: { score_stable_eps?: number };
};

export const benchmarksApi = {
  list: () =>
    apiClient
      .get<{ items: Benchmark[]; total: number }>("/benchmarks")
      .then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Benchmark>(`/benchmarks/${id}`).then((r) => r.data),

  create: (body: {
    name: string;
    description?: string;
    tags?: string[];
    cases?: BenchmarkCase[];
    version?: string;
    scorecard?: Record<string, unknown>;
    source_task_id?: string;
  }) =>
    apiClient.post<Benchmark>("/benchmarks", body).then((r) => r.data),

  importCases: (id: string, content: string, format: "json" | "csv" = "json") =>
    apiClient
      .post<{ imported: number }>(`/benchmarks/${id}/import`, { content, format })
      .then((r) => r.data),

  run: (
    id: string,
    body?: {
      label?: string;
      agent_config?: Record<string, unknown>;
      enqueue?: boolean;
    }
  ) =>
    apiClient
      .post<{ run: BenchmarkRun }>(`/benchmarks/${id}/run`, body || {})
      .then((r) => r.data),

  listRuns: (id: string, limit = 50) =>
    apiClient
      .get<{ items: BenchmarkRun[]; total: number; benchmark_id: string }>(
        `/benchmarks/${id}/runs`,
        { params: { limit } }
      )
      .then((r) => r.data),

  finalizeRun: (id: string, runId: string) =>
    apiClient
      .post<{ run: BenchmarkRun }>(`/benchmarks/${id}/runs/${runId}/finalize`)
      .then((r) => r.data),

  compare: (
    id: string,
    body: {
      current_run_id: string;
      baseline_run_id?: string | null;
      score_stable_eps?: number;
    }
  ) =>
    apiClient
      .post<RunComparison>(`/benchmarks/${id}/compare`, body)
      .then((r) => r.data),

  leaderboard: (id: string) =>
    apiClient
      .get<{ items: LeaderboardRow[]; total: number; metrics: string[] }>(
        `/benchmarks/${id}/leaderboard`
      )
      .then((r) => r.data),
};

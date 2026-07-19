/* (c) 2026 AgentFlow-Eval */
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
  summary?: Record<string, unknown>;
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

  leaderboard: (id: string) =>
    apiClient
      .get<{ items: LeaderboardRow[]; total: number; metrics: string[] }>(
        `/benchmarks/${id}/leaderboard`
      )
      .then((r) => r.data),
};

/* (c) 2026 AgentFlow-Eval */
import { apiClient } from "../client";

export type DiagnosisIssue =
  | "agent_loop"
  | "tool_failure"
  | "token_drift"
  | "prompt_drift"
  | "timeout"
  | "healthy"
  | string;

export type DiagnosisResult = {
  task_id?: string | null;
  task_name?: string | null;
  task_status?: string | null;
  issue: DiagnosisIssue;
  confidence: number;
  root_cause: string;
  suggestion: string;
  issues?: Array<{
    issue: DiagnosisIssue;
    confidence: number;
    root_cause: string;
    suggestion: string;
    evidence?: Record<string, unknown>;
  }>;
  summary?: {
    traces_total: number;
    traces_success: number;
    traces_failed: number;
    suites_total: number;
    avg_latency_ms: number;
    total_tokens: number;
    total_cost: number;
  };
  topology?: {
    nodes: Array<{ id: string; label: string; status?: string }>;
    edges: Array<{ source: string; target: string; type?: string }>;
  };
  token_curve?: Array<{
    trace_id: string;
    tokens: number;
    latency_ms?: number;
    status?: string;
  }>;
  prompt_versions?: string[];
};

export type DiagnosisListItem = {
  task_id?: string | null;
  task_name?: string | null;
  task_status?: string | null;
  issue: DiagnosisIssue;
  confidence: number;
  root_cause: string;
  suggestion: string;
};

export const diagnosisApi = {
  list: (limit = 10) =>
    apiClient
      .get<{ items: DiagnosisListItem[]; total: number }>("/diagnosis", {
        params: { limit },
      })
      .then((r) => r.data),

  byTask: (taskId: string) =>
    apiClient.get<DiagnosisResult>(`/diagnosis/${taskId}`).then((r) => r.data),

  byTrace: (traceId: string) =>
    apiClient
      .get<DiagnosisResult>(`/diagnosis/trace/${traceId}`)
      .then((r) => r.data),
};

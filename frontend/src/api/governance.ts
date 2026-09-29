import { apiClient } from "./client";

export type QualityGateRow = {
  agent_id: string;
  agent_name: string;
  current_version: string | null;
  latest_evaluation_id: string | null;
  evaluation_score: number | null;
  evaluation_status: string | null;
  benchmark_id: string | null;
  benchmark_delta: number | null;
  benchmark_status: string | null;
  quality_gate: string | null;
  release_assessment_id: string | null;
  deployment_status: string;
};

export type GovernanceEvaluationDetail = {
  evaluation_id: string;
  agent_id: string;
  agent_version: string;
  status: string;
  score: number | null;
  metrics: Record<string, number>;
  judge_mode: string | null;
  token_cost: number;
  completed_at: string | null;
  started_at: string;
  failures: Array<{
    case_name: string;
    status: string;
    score: number;
    reason: string;
  }>;
  metadata: Record<string, unknown>;
};

export type GovernanceBenchmarkDetail = {
  benchmark_id: string;
  agent_id: string;
  baseline_version: string;
  candidate_version: string;
  status: string;
  metric_comparison: Record<string, number | null | undefined>;
  score_delta: number | null;
  baseline_score: number | null;
  candidate_score: number | null;
  regression_detected: boolean | null;
  decision: string;
  started_at: string;
  completed_at: string | null;
  metadata: Record<string, unknown>;
};

export type GovernanceReleaseDetail = {
  assessment_id: string;
  agent_id: string;
  version: string;
  decision: string;
  score: number | null;
  score_delta: number | null;
  regression_detected: boolean | null;
  reasons: string[];
  evaluation_id: string | null;
  benchmark_id: string | null;
  baseline_version: string | null;
  policy_min_score: number | null;
  assessed_at: string;
  metadata: Record<string, unknown>;
  policy?: {
    agent_id: string;
    min_score: number | null;
    required_metrics: Record<string, number>;
    evaluation_required: boolean;
    gate_enabled: boolean;
  };
};

export type DeploymentPolicyRow = {
  agent_id: string;
  agent_name?: string;
  min_score: number | null;
  required_metrics: Record<string, number>;
  evaluation_required: boolean;
  gate_enabled: boolean;
};

export const governanceApi = {
  listQualityGates: () =>
    apiClient
      .get<{ items: QualityGateRow[]; count: number }>("/governance/quality-gates")
      .then((r) => r.data),

  getEvaluation: (evaluationId: string) =>
    apiClient
      .get<{ evaluation: GovernanceEvaluationDetail }>(
        `/governance/evaluations/${evaluationId}`,
      )
      .then((r) => r.data.evaluation),

  getBenchmark: (benchmarkId: string) =>
    apiClient
      .get<{ benchmark: GovernanceBenchmarkDetail }>(
        `/governance/benchmarks/${benchmarkId}`,
      )
      .then((r) => r.data.benchmark),

  getReleaseAssessment: (assessmentId: string) =>
    apiClient
      .get<{ assessment: GovernanceReleaseDetail }>(`/governance/releases/${assessmentId}`)
      .then((r) => r.data.assessment),

  listDeploymentPolicies: () =>
    apiClient
      .get<{ policies: DeploymentPolicyRow[]; count: number }>("/governance/policies")
      .then((r) => r.data),
};

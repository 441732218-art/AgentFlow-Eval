/** Agent Management & Runtime execution types (V2.3 product API). */

export interface AgentSummary {
  id: string;
  name: string;
  version: string;
  enabled: boolean;
  description: string;
  lifecycle_status?: string;
  current_active_version?: string;
}

/** Fleet row merged from agent, governance, deployment, and observability sources. */
export interface AgentFleetRow extends AgentSummary {
  environment?: string | null;
  quality_gate?: string | null;
  last_execution_id?: string | null;
  last_execution_status?: string | null;
  last_execution_at?: string | null;
}

export interface AgentVersionRow extends AgentVersion {
  created_at?: string | null;
  evaluation_score?: number | null;
  benchmark_result?: string | null;
  deployment_status?: string | null;
}

export interface AgentDetail extends AgentSummary {
  tool_names: string[];
  system_prompt: string;
  model_config: Record<string, unknown>;
  roles: string[];
}

export interface AgentCreatePayload {
  id: string;
  name: string;
  description?: string;
  tool_names?: string[];
  system_prompt?: string;
  model_config?: Record<string, unknown>;
  enabled?: boolean;
  roles?: string[];
}

export interface AgentUpdatePayload {
  name: string;
  description?: string;
  tool_names?: string[];
  system_prompt?: string;
  model_config?: Record<string, unknown>;
  enabled?: boolean;
  roles?: string[];
}

export interface AgentVersion {
  agent_id: string;
  version: string;
  status: string;
  definition: AgentDetail;
}

export interface AgentDeployment {
  agent_id: string;
  version: string;
  environment: string;
  status: "ACTIVE" | "INACTIVE" | "ROLLBACK" | string;
}

export interface RuntimeExecuteResponse {
  execution_id: string;
  status: string;
  output: unknown;
  error: string | null;
}

export interface RuntimeExecutionDetail {
  execution_id: string;
  status: string;
  output: unknown;
  error: string | null;
  created_at?: string;
  updated_at?: string;
  agent_id?: string;
  duration_ms?: number;
  trace_available?: boolean;
}

export interface TraceStep {
  type: string;
  timestamp?: string;
  tool_name?: string;
  status?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
}

export interface TraceEntryDto {
  trace_id: string;
  execution_id: string;
  timestamp: string;
  event_type: string;
  source: string;
  status?: string;
  agent_id?: string;
  workflow_id?: string;
  node_id?: string;
  tool_name?: string;
  duration_ms?: number;
  metadata?: Record<string, unknown>;
}

export interface ToolHistoryItem {
  event_type: string;
  timestamp: string;
  tool_name?: string | null;
  status?: string | null;
  duration_ms?: number | null;
}

export interface ExecutionEvidence {
  execution_id: string;
  tenant_id?: string | null;
  actor_id?: string | null;
  agent_id?: string | null;
  agent_version?: string | null;
  deployment_environment?: string | null;
  release_decision?: string | null;
  evaluation_score?: number | null;
  started_at?: string | null;
  completed_at?: string | null;
  status?: string | null;
  events?: Array<{ event_type: string; timestamp: string; metadata?: Record<string, unknown> }>;
  tool_history?: ToolHistoryItem[];
}

export interface ExecutionTraceResponse {
  execution_id: string;
  trace: TraceEntryDto[];
  /** @deprecated legacy alias */
  steps?: TraceStep[];
}

export interface AgentListResponse {
  agents: AgentSummary[];
  count: number;
}

export interface AgentVersionsResponse {
  versions: AgentVersion[];
  count: number;
}

export interface AgentDeploymentsResponse {
  deployments: AgentDeployment[];
  count: number;
}

export interface EvaluationSummary {
  evaluation_id: string;
  agent_id: string;
  agent_version: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  score: number | null;
  score_summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface EvaluationResult {
  case_name: string;
  total: number;
  scores: Record<string, number>;
  reason: string;
  token_cost: number;
  status: string;
  execution_id?: string;
  judge_mode?: string;
}

export interface EvaluationDetail extends EvaluationSummary {
  results: EvaluationResult[];
}

export interface AgentEvaluationsResponse {
  evaluations: EvaluationSummary[];
  count: number;
}

export interface DeploymentPolicy {
  agent_id: string;
  min_score: number | null;
  required_metrics: Record<string, number>;
  evaluation_required: boolean;
  gate_enabled: boolean;
}

export interface DeploymentGateStatus {
  agent_id: string;
  agent_version: string;
  allowed: boolean;
  status: string;
  reason: string | null;
  latest_score: number | null;
  latest_evaluation_id: string | null;
  policy?: DeploymentPolicy;
}

export interface DeploymentPolicyPayload {
  min_score?: number | null;
  required_metrics?: Record<string, number>;
  evaluation_required?: boolean;
}

export interface BenchmarkComparison {
  baseline_score: number;
  candidate_score: number;
  score_delta: number;
  metric_delta: Record<string, number>;
  regression_detected: boolean;
  baseline_evaluation_id: string;
  candidate_evaluation_id: string;
}

export interface VersionBenchmarkSummary {
  benchmark_id: string;
  agent_id: string;
  baseline_version: string;
  candidate_version: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  baseline_score: number | null;
  candidate_score: number | null;
  score_delta: number | null;
  regression_detected: boolean | null;
  metadata: Record<string, unknown>;
}

export interface VersionBenchmarkDetail extends VersionBenchmarkSummary {
  comparison: BenchmarkComparison | null;
}

export interface AgentBenchmarksResponse {
  benchmarks: VersionBenchmarkSummary[];
  count: number;
}

export interface ReleaseAssessment {
  assessment_id: string;
  agent_id: string;
  version: string;
  decision: "APPROVE" | "REJECT" | "WARNING" | string;
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
}

export interface ReleaseAssessmentsResponse {
  assessments: ReleaseAssessment[];
  count: number;
}

export interface ReleaseAssessmentPayload {
  version: string;
  benchmark_id?: string;
  metadata?: Record<string, unknown>;
}

export interface StartBenchmarkPayload {
  baseline_version: string;
  candidate_version: string;
  test_cases?: Array<{
    name: string;
    user_query?: string;
    expected_output?: string;
    expected_tools?: string[];
    trace_steps?: Record<string, unknown>[];
  }>;
  metadata?: Record<string, unknown>;
}

export interface StartEvaluationPayload {
  agent_version: string;
  test_cases?: Array<{
    name: string;
    user_query?: string;
    expected_output?: string;
    expected_tools?: string[];
    trace_steps?: Record<string, unknown>[];
  }>;
  metadata?: Record<string, unknown>;
}

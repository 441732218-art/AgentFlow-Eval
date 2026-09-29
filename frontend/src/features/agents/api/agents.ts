import { apiClient } from "@/api/client";
import type {
  AgentCreatePayload,
  AgentDeploymentsResponse,
  AgentDetail,
  AgentEvaluationsResponse,
  AgentListResponse,
  AgentUpdatePayload,
  AgentVersionsResponse,
  AgentVersion,
  AgentDeployment,
  DeploymentGateStatus,
  DeploymentPolicy,
  DeploymentPolicyPayload,
  EvaluationDetail,
  ExecutionEvidence,
  ExecutionTraceResponse,
  RuntimeExecuteResponse,
  RuntimeExecutionDetail,
  ReleaseAssessment,
  ReleaseAssessmentPayload,
  ReleaseAssessmentsResponse,
  StartBenchmarkPayload,
  StartEvaluationPayload,
  VersionBenchmarkDetail,
  AgentBenchmarksResponse,
} from "../types/agent";

/** Unified Agent Console API — all HTTP calls go through this module. */
export const agentsApi = {
  listAgents: () =>
    apiClient.get<AgentListResponse>("/agents").then((r) => r.data),

  getAgent: (agentId: string) =>
    apiClient.get<{ agent: AgentDetail }>(`/agents/${agentId}`).then((r) => r.data.agent),

  createAgent: (payload: AgentCreatePayload) =>
    apiClient.post<{ agent: AgentDetail }>("/agents", payload).then((r) => r.data.agent),

  updateAgent: (agentId: string, payload: AgentUpdatePayload) =>
    apiClient
      .put<{ agent: AgentDetail }>(`/agents/${agentId}`, payload)
      .then((r) => r.data.agent),

  listVersions: (agentId: string) =>
    apiClient
      .get<AgentVersionsResponse>(`/agents/${agentId}/versions`)
      .then((r) => r.data),

  publishVersion: (agentId: string, version: string) =>
    apiClient
      .post<{ version: AgentVersion }>(`/agents/${agentId}/versions`, { version })
      .then((r) => r.data.version),

  listDeployments: (agentId: string) =>
    apiClient
      .get<AgentDeploymentsResponse>(`/agents/${agentId}/deployments`)
      .then((r) => r.data),

  deployVersion: (agentId: string, version: string, environment = "production") =>
    apiClient
      .post<{ deployment: AgentDeployment }>(`/agents/${agentId}/deployments`, {
        version,
        environment,
      })
      .then((r) => r.data.deployment),

  rollbackDeployment: (agentId: string, environment = "production") =>
    apiClient
      .post<{ deployment: AgentDeployment }>(
        `/agents/${agentId}/deployments/rollback`,
        { environment },
      )
      .then((r) => r.data.deployment),

  executeAgent: (agentId: string, task: string, context?: Record<string, unknown>) =>
    apiClient
      .post<RuntimeExecuteResponse>("/runtime/execute", {
        agent_id: agentId,
        task,
        context: context ?? {},
      })
      .then((r) => r.data),

  getExecution: (executionId: string) =>
    apiClient
      .get<RuntimeExecutionDetail>(`/runtime/executions/${executionId}`)
      .then((r) => r.data),

  getExecutionTrace: (executionId: string) =>
    apiClient
      .get<ExecutionTraceResponse>(`/runtime/executions/${executionId}/trace`)
      .then((r) => r.data),

  getExecutionEvidence: (executionId: string) =>
    apiClient
      .get<{ evidence: ExecutionEvidence }>(`/runtime/executions/${executionId}/evidence`)
      .then((r) => r.data.evidence),

  listExecutions: (params: { agent_id?: string; status?: string; limit?: number; offset?: number } = {}) =>
    apiClient
      .get<{
        items: RuntimeExecutionDetail[];
        total?: number;
        limit?: number;
      }>("/runtime/executions", { params })
      .then((r) => r.data),

  listEvaluations: (agentId: string) =>
    apiClient
      .get<AgentEvaluationsResponse>(`/agents/${agentId}/evaluations`)
      .then((r) => r.data),

  startEvaluation: (agentId: string, payload: StartEvaluationPayload) =>
    apiClient
      .post<{ evaluation: EvaluationDetail }>(`/agents/${agentId}/evaluations`, payload)
      .then((r) => r.data.evaluation),

  getEvaluation: (evaluationId: string) =>
    apiClient
      .get<{ evaluation: EvaluationDetail }>(`/evaluations/${evaluationId}`)
      .then((r) => r.data.evaluation),

  getDeploymentPolicy: (agentId: string) =>
    apiClient
      .get<{ policy: DeploymentPolicy }>(`/agents/${agentId}/deployment-policy`)
      .then((r) => r.data.policy),

  updateDeploymentPolicy: (agentId: string, payload: DeploymentPolicyPayload) =>
    apiClient
      .put<{ policy: DeploymentPolicy }>(`/agents/${agentId}/deployment-policy`, payload)
      .then((r) => r.data.policy),

  getDeploymentGate: (agentId: string, version: string) =>
    apiClient
      .get<{ gate: DeploymentGateStatus }>(`/agents/${agentId}/deployment-gate/${version}`)
      .then((r) => r.data.gate),

  listBenchmarks: (agentId: string) =>
    apiClient
      .get<AgentBenchmarksResponse>(`/agents/${agentId}/benchmarks`)
      .then((r) => r.data),

  startBenchmark: (agentId: string, payload: StartBenchmarkPayload) =>
    apiClient
      .post<{ benchmark: VersionBenchmarkDetail }>(`/agents/${agentId}/benchmarks`, payload)
      .then((r) => r.data.benchmark),

  getBenchmark: (benchmarkId: string) =>
    apiClient
      .get<{ benchmark: VersionBenchmarkDetail }>(`/agent-benchmarks/${benchmarkId}`)
      .then((r) => r.data.benchmark),

  listReleaseAssessments: (agentId: string) =>
    apiClient
      .get<ReleaseAssessmentsResponse>(`/agents/${agentId}/release-assessments`)
      .then((r) => r.data),

  createReleaseAssessment: (agentId: string, payload: ReleaseAssessmentPayload) =>
    apiClient
      .post<{ assessment: ReleaseAssessment }>(`/agents/${agentId}/release-assessments`, payload)
      .then((r) => r.data.assessment),
};

/**
 * V2.3 RC — Frontend API client paths vs frozen OpenAPI contract.
 * Static validation only; no network calls.
 */
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const AGENTS_PATHS = [
  '"/agents"',
  "`/agents/${agentId}`",
  "`/agents/${agentId}/versions`",
  "`/agents/${agentId}/deployments`",
  "`/agents/${agentId}/deployments/rollback`",
  '"/runtime/execute"',
  "`/runtime/executions/${executionId}`",
  "`/runtime/executions/${executionId}/trace`",
  "`/runtime/executions/${executionId}/evidence`",
  '"/runtime/executions"',
  "`/agents/${agentId}/evaluations`",
  "`/evaluations/${evaluationId}`",
  "`/agents/${agentId}/deployment-policy`",
  "`/agents/${agentId}/deployment-gate/${version}`",
  "`/agents/${agentId}/benchmarks`",
  "`/agent-benchmarks/${benchmarkId}`",
  "`/agents/${agentId}/release-assessments`",
];

const GOVERNANCE_PATHS = [
  '"/governance/quality-gates"',
  "`/governance/evaluations/${evaluationId}`",
  "`/governance/benchmarks/${benchmarkId}`",
  "`/governance/releases/${assessmentId}`",
  '"/governance/policies"',
];

const RUNTIME_PATHS = ['"/runtime/executions"', "`/runtime/executions/${executionId}`"];

function readSource(relativePath: string): string {
  return readFileSync(resolve(__dirname, relativePath), "utf-8");
}

describe("V2.3 RC frontend API contract", () => {
  it("agentsApi covers frozen agent/runtime paths", () => {
    const source = readSource("agents.ts");
    for (const path of AGENTS_PATHS) {
      expect(source, `missing ${path}`).toContain(path);
    }
  });

  it("governanceApi covers frozen governance paths", () => {
    const source = readSource("../../../api/governance.ts");
    for (const path of GOVERNANCE_PATHS) {
      expect(source, `missing ${path}`).toContain(path);
    }
  });

  it("runtimeApi covers frozen runtime list/detail paths", () => {
    const source = readSource("../../../api/runtime.ts");
    for (const path of RUNTIME_PATHS) {
      expect(source, `missing ${path}`).toContain(path);
    }
  });

  it("governanceApi response shapes match backend wrappers", () => {
    const governanceSource = readSource("../../../api/governance.ts");
    expect(governanceSource).toContain("get<{ items: QualityGateRow[]; count: number }>");
    expect(governanceSource).toContain("{ evaluation: GovernanceEvaluationDetail }");
    expect(governanceSource).toContain("{ benchmark: GovernanceBenchmarkDetail }");
    expect(governanceSource).toContain("{ assessment: GovernanceReleaseDetail }");
    expect(governanceSource).toContain("{ policies: DeploymentPolicyRow[]; count: number }");
  });

  it("agentsApi execute payload matches RuntimeExecuteRequest", () => {
    const agentsSource = readSource("agents.ts");
    expect(agentsSource).toContain('post<RuntimeExecuteResponse>("/runtime/execute"');
    expect(agentsSource).toContain("agent_id: agentId");
    expect(agentsSource).toContain("task,");
    expect(agentsSource).toContain("context:");
  });

  it("deployment gate response uses gate wrapper", () => {
    const agentsSource = readSource("agents.ts");
    expect(agentsSource).toContain("{ gate: DeploymentGateStatus }");
  });
});

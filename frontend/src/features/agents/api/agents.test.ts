import { describe, it, expect, vi, beforeEach } from "vitest";
import { agentsApi } from "./agents";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";

const getMock = apiClient.get as unknown as ReturnType<typeof vi.fn>;
const postMock = apiClient.post as unknown as ReturnType<typeof vi.fn>;

describe("agentsApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("listAgents calls GET /agents", async () => {
    getMock.mockResolvedValue({
      data: { agents: [{ id: "a1", name: "Agent", version: "1.0", enabled: true, description: "" }], count: 1 },
    });
    const result = await agentsApi.listAgents();
    expect(getMock).toHaveBeenCalledWith("/agents");
    expect(result.count).toBe(1);
  });

  it("publishVersion posts version label", async () => {
    postMock.mockResolvedValue({
      data: { version: { agent_id: "a1", version: "1.1", status: "ACTIVE", definition: {} } },
    });
    await agentsApi.publishVersion("a1", "1.1");
    expect(postMock).toHaveBeenCalledWith("/agents/a1/versions", { version: "1.1" });
  });

  it("deployVersion posts environment", async () => {
    postMock.mockResolvedValue({
      data: { deployment: { agent_id: "a1", version: "1.0", environment: "production", status: "ACTIVE" } },
    });
    await agentsApi.deployVersion("a1", "1.0", "production");
    expect(postMock).toHaveBeenCalledWith("/agents/a1/deployments", {
      version: "1.0",
      environment: "production",
    });
  });

  it("benchmark endpoints call agent benchmark API", async () => {
    postMock.mockResolvedValue({
      data: {
        benchmark: {
          benchmark_id: "bm-1",
          agent_id: "a1",
          baseline_version: "1.0",
          candidate_version: "1.1",
          status: "completed",
          started_at: "",
          completed_at: "",
          comparison: {
            baseline_score: 78,
            candidate_score: 91,
            score_delta: 13,
            metric_delta: {},
            regression_detected: false,
            baseline_evaluation_id: "e1",
            candidate_evaluation_id: "e2",
          },
          metadata: {},
        },
      },
    });
    await agentsApi.startBenchmark("a1", { baseline_version: "1.0", candidate_version: "1.1" });
    expect(postMock).toHaveBeenCalledWith("/agents/a1/benchmarks", {
      baseline_version: "1.0",
      candidate_version: "1.1",
    });

    getMock.mockResolvedValueOnce({ data: { benchmarks: [], count: 0 } });
    await agentsApi.listBenchmarks("a1");
    expect(getMock).toHaveBeenCalledWith("/agents/a1/benchmarks");
  });

  it("release assessment endpoints call release API", async () => {
    postMock.mockResolvedValue({
      data: {
        assessment: {
          assessment_id: "ra-1",
          agent_id: "a1",
          version: "1.1",
          decision: "WARNING",
          score: 85,
          score_delta: null,
          regression_detected: null,
          reasons: ["no benchmark comparison on record"],
          evaluation_id: "e1",
          benchmark_id: null,
          baseline_version: null,
          policy_min_score: 80,
          assessed_at: "",
          metadata: {},
        },
      },
    });
    await agentsApi.createReleaseAssessment("a1", { version: "1.1" });
    expect(postMock).toHaveBeenCalledWith("/agents/a1/release-assessments", { version: "1.1" });

    getMock.mockResolvedValueOnce({ data: { assessments: [], count: 0 } });
    await agentsApi.listReleaseAssessments("a1");
    expect(getMock).toHaveBeenCalledWith("/agents/a1/release-assessments");
  });

  it("evaluation endpoints call agent evaluation API", async () => {
    postMock.mockResolvedValue({
      data: {
        evaluation: {
          evaluation_id: "ev-1",
          agent_id: "a1",
          agent_version: "1.0",
          status: "completed",
          started_at: "",
          completed_at: "",
          score_summary: {},
          metadata: {},
          results: [],
        },
      },
    });
    await agentsApi.startEvaluation("a1", { agent_version: "1.0" });
    expect(postMock).toHaveBeenCalledWith("/agents/a1/evaluations", {
      agent_version: "1.0",
    });

    getMock.mockResolvedValueOnce({ data: { evaluations: [], count: 0 } });
    await agentsApi.listEvaluations("a1");
    expect(getMock).toHaveBeenCalledWith("/agents/a1/evaluations");
  });

  it("executeAgent calls runtime execute endpoint", async () => {
    postMock.mockResolvedValue({
      data: { execution_id: "exec-1", status: "SUCCESS", output: {}, error: null },
    });
    const result = await agentsApi.executeAgent("trade.sales_agent", "hello");
    expect(postMock).toHaveBeenCalledWith("/runtime/execute", {
      agent_id: "trade.sales_agent",
      task: "hello",
      context: {},
    });
    expect(result.execution_id).toBe("exec-1");
  });

  it("listExecutions calls GET /runtime/executions", async () => {
    getMock.mockResolvedValue({
      data: {
        items: [{ execution_id: "exec-1", agent_id: "a1", status: "SUCCESS" }],
        total: 1,
      },
    });
    const result = await agentsApi.listExecutions({ agent_id: "a1", limit: 20 });
    expect(getMock).toHaveBeenCalledWith("/runtime/executions", {
      params: { agent_id: "a1", limit: 20 },
    });
    expect(result.items).toHaveLength(1);
  });

  it("getExecutionTrace calls trace endpoint", async () => {
    getMock.mockResolvedValue({
      data: {
        execution_id: "exec-1",
        trace: [{ trace_id: "t1", event_type: "agent.started", source: "runtime", timestamp: "" }],
      },
    });
    const trace = await agentsApi.getExecutionTrace("exec-1");
    expect(getMock).toHaveBeenCalledWith("/runtime/executions/exec-1/trace");
    expect(trace.trace).toHaveLength(1);
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import AgentList from "./AgentList";
import AgentDetailLayout from "./AgentDetail";
import AgentVersions from "./AgentVersions";
import AgentDeployments from "./AgentDeployments";
import AgentExecutions from "./AgentExecutions";
import AgentTrace from "./AgentTrace";

vi.mock("@/auth/RouteGuard", () => ({
  RouteGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/api/governance", () => ({
  governanceApi: {
    listQualityGates: vi.fn(),
  },
}));

vi.mock("@/api/runtime", () => ({
  runtimeApi: {
    listExecutions: vi.fn(),
    getExecution: vi.fn(),
  },
}));

vi.mock("../api/agents", () => ({
  agentsApi: {
    listAgents: vi.fn(),
    getAgent: vi.fn(),
    listVersions: vi.fn(),
    listDeployments: vi.fn(),
    listEvaluations: vi.fn(),
    listBenchmarks: vi.fn(),
    getExecutionTrace: vi.fn(),
    getExecutionEvidence: vi.fn(),
    updateAgent: vi.fn(),
  },
}));

import { governanceApi } from "@/api/governance";
import { runtimeApi } from "@/api/runtime";
import { agentsApi } from "../api/agents";

const sampleAgent = {
  id: "support.agent",
  name: "Support Agent",
  version: "draft",
  enabled: true,
  description: "Help desk",
  lifecycle_status: "ACTIVE",
  current_active_version: "1.0",
  tool_names: ["trade.search_customer"],
  system_prompt: "You are helpful",
  model_config: {},
  roles: [],
};

function AgentTabHarness({ tab }: { tab: string }) {
  return (
    <MemoryRouter initialEntries={[`/agents/support.agent/${tab}`]}>
      <Routes>
        <Route path="/agents/:id" element={<AgentDetailLayout />}>
          <Route path="versions" element={<AgentVersions />} />
          <Route path="deployments" element={<AgentDeployments />} />
          <Route path="executions" element={<AgentExecutions />} />
          <Route path="trace" element={<AgentTrace />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("Agent Operations Console", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (agentsApi.getAgent as ReturnType<typeof vi.fn>).mockResolvedValue(sampleAgent);
  });

  it("AgentList renders fleet rows", async () => {
    (agentsApi.listAgents as ReturnType<typeof vi.fn>).mockResolvedValue({
      agents: [sampleAgent],
      count: 1,
    });
    (governanceApi.listQualityGates as ReturnType<typeof vi.fn>).mockResolvedValue({
      count: 1,
      items: [
        {
          agent_id: "support.agent",
          agent_name: "Support Agent",
          current_version: "1.0",
          quality_gate: "APPROVED",
          deployment_status: "production",
        },
      ],
    });
    (runtimeApi.listExecutions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          execution_id: "exec-1",
          agent_id: "support.agent",
          status: "SUCCESS",
          started_at: "2026-01-01T00:00:00Z",
        },
      ],
    });

    render(
      <MemoryRouter>
        <AgentList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Support Agent")).toBeInTheDocument();
    });
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();
  });

  it("AgentDetail renders overview and tabs", async () => {
    (runtimeApi.listExecutions as ReturnType<typeof vi.fn>).mockResolvedValue({ items: [] });

    render(
      <MemoryRouter initialEntries={["/agents/support.agent/overview"]}>
        <Routes>
          <Route path="/agents/:id/*" element={<AgentDetailLayout />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Support Agent")).toBeInTheDocument();
    });
    expect(screen.getByText("Governance")).toBeInTheDocument();
    expect(screen.getByText("Recent Executions (last 20)")).toBeInTheDocument();
  });

  it("Version tab renders read-only registry", async () => {
    (agentsApi.listVersions as ReturnType<typeof vi.fn>).mockResolvedValue({
      versions: [
        {
          agent_id: "support.agent",
          version: "1.0",
          status: "ACTIVE",
          created_at: "2026-01-01T00:00:00Z",
          definition: sampleAgent,
        },
      ],
      count: 1,
    });
    (agentsApi.listEvaluations as ReturnType<typeof vi.fn>).mockResolvedValue({
      evaluations: [],
      count: 0,
    });
    (agentsApi.listBenchmarks as ReturnType<typeof vi.fn>).mockResolvedValue({
      benchmarks: [],
      count: 0,
    });
    (agentsApi.listDeployments as ReturnType<typeof vi.fn>).mockResolvedValue({
      deployments: [
        {
          agent_id: "support.agent",
          version: "1.0",
          environment: "production",
          status: "ACTIVE",
        },
      ],
      count: 1,
    });

    render(<AgentTabHarness tab="versions" />);

    await waitFor(() => {
      expect(screen.getByText("Version Registry")).toBeInTheDocument();
    });
    expect(screen.getByText("Read-only view")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByText("1.0").length).toBeGreaterThan(0);
    });
  });

  it("Deployment tab renders read-only table", async () => {
    (agentsApi.listDeployments as ReturnType<typeof vi.fn>).mockResolvedValue({
      deployments: [
        {
          agent_id: "support.agent",
          version: "1.0",
          environment: "production",
          status: "ACTIVE",
        },
      ],
      count: 1,
    });

    render(<AgentTabHarness tab="deployments" />);

    await waitFor(() => {
      expect(screen.getByText("Read-only deployment view")).toBeInTheDocument();
    });
    expect(screen.getByText("production")).toBeInTheDocument();
  });

  it("Execution tab renders execution rows", async () => {
    (runtimeApi.listExecutions as ReturnType<typeof vi.fn>).mockResolvedValue({
      items: [
        {
          execution_id: "exec-99",
          agent_id: "support.agent",
          status: "FAILED",
          duration: 1.2,
          trace_available: true,
        },
      ],
    });

    render(<AgentTabHarness tab="executions" />);

    await waitFor(() => {
      expect(screen.getByText("exec-99")).toBeInTheDocument();
    });
    expect(screen.getByText("FAILED")).toBeInTheDocument();
  });

  it("Trace navigation loads from query param", async () => {
    (agentsApi.getExecutionTrace as ReturnType<typeof vi.fn>).mockResolvedValue({
      execution_id: "exec-trace",
      trace: [{ trace_id: "t1", event_type: "agent.started", source: "runtime", timestamp: "" }],
    });
    (agentsApi.getExecutionEvidence as ReturnType<typeof vi.fn>).mockResolvedValue({
      execution_id: "exec-trace",
      status: "SUCCESS",
    });

    render(
      <MemoryRouter initialEntries={["/agents/support.agent/trace?executionId=exec-trace"]}>
        <Routes>
          <Route path="/agents/:id" element={<AgentDetailLayout />}>
            <Route path="trace" element={<AgentTrace />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(agentsApi.getExecutionTrace).toHaveBeenCalledWith("exec-trace");
    });
  });
});

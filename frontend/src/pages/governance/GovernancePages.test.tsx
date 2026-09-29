import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import BenchmarkDetailPage from "./BenchmarkDetail";
import ReleaseAssessmentDetailPage from "./ReleaseAssessmentDetail";

vi.mock("@/api/governance", () => ({
  governanceApi: {
    getBenchmark: vi.fn(),
    getReleaseAssessment: vi.fn(),
  },
}));

import { governanceApi } from "@/api/governance";

const getBenchmarkMock = governanceApi.getBenchmark as unknown as ReturnType<typeof vi.fn>;
const getReleaseMock = governanceApi.getReleaseAssessment as unknown as ReturnType<typeof vi.fn>;

describe("Governance detail pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders benchmark comparison", async () => {
    getBenchmarkMock.mockResolvedValue({
      benchmark_id: "bench-1",
      agent_id: "support.agent",
      baseline_version: "v1.1",
      candidate_version: "v1.2",
      status: "completed",
      metric_comparison: { accuracy: 0.08, latency: -0.12, cost: 0.05 },
      score_delta: 5,
      baseline_score: 87,
      candidate_score: 92,
      regression_detected: false,
      decision: "PASS",
      started_at: "2026-01-01T00:00:00Z",
      completed_at: "2026-01-01T00:05:00Z",
      metadata: {},
    });

    render(
      <MemoryRouter initialEntries={["/governance/benchmarks/bench-1"]}>
        <Routes>
          <Route path="/governance/benchmarks/:id" element={<BenchmarkDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("v1.1")).toBeInTheDocument();
    });
    expect(screen.getByText("PASS")).toBeInTheDocument();
  });

  it("renders release decision", async () => {
    getReleaseMock.mockResolvedValue({
      assessment_id: "rel-1",
      agent_id: "support.agent",
      version: "v1.2",
      decision: "APPROVED",
      score: 92,
      score_delta: 5,
      regression_detected: false,
      reasons: ["Score meets policy"],
      evaluation_id: "eval-1",
      benchmark_id: "bench-1",
      baseline_version: "v1.1",
      policy_min_score: 80,
      assessed_at: "2026-01-01T00:10:00Z",
      metadata: {},
      policy: {
        agent_id: "support.agent",
        min_score: 80,
        required_metrics: {},
        evaluation_required: true,
        gate_enabled: true,
      },
    });

    render(
      <MemoryRouter initialEntries={["/governance/releases/rel-1"]}>
        <Routes>
          <Route path="/governance/releases/:id" element={<ReleaseAssessmentDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("APPROVED")).toBeInTheDocument();
    });
  });
});

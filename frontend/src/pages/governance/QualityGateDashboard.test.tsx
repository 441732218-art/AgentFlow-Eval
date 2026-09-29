import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import QualityGateDashboard from "./QualityGateDashboard";

vi.mock("@/api/governance", () => ({
  governanceApi: {
    listQualityGates: vi.fn(),
  },
}));

vi.mock("@/auth/RouteGuard", () => ({
  RouteGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { governanceApi } from "@/api/governance";

const listMock = governanceApi.listQualityGates as unknown as ReturnType<typeof vi.fn>;

describe("QualityGateDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders quality gate rows", async () => {
    listMock.mockResolvedValue({
      count: 1,
      items: [
        {
          agent_id: "support.agent",
          agent_name: "Customer Support Agent",
          current_version: "v1.2",
          latest_evaluation_id: "eval-1",
          evaluation_score: 92,
          evaluation_status: "completed",
          benchmark_id: "bench-1",
          benchmark_delta: 5,
          benchmark_status: "stable",
          quality_gate: "APPROVED",
          release_assessment_id: "rel-1",
          deployment_status: "production",
        },
      ],
    });

    render(
      <MemoryRouter>
        <QualityGateDashboard />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Customer Support Agent")).toBeInTheDocument();
    });
    expect(screen.getByText("APPROVED")).toBeInTheDocument();
  });

  it("renders API error state", async () => {
    listMock.mockRejectedValue(new Error("Backend unavailable"));

    render(
      <MemoryRouter>
        <QualityGateDashboard />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Unable to load quality gates")).toBeInTheDocument();
    });
  });
});

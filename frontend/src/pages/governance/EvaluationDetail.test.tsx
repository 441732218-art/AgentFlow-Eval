import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, waitFor } from "@testing-library/react";
import EvaluationDetailPage from "./EvaluationDetail";

vi.mock("@/api/governance", () => ({
  governanceApi: {
    getEvaluation: vi.fn(),
  },
}));

import { governanceApi } from "@/api/governance";

const getMock = governanceApi.getEvaluation as unknown as ReturnType<typeof vi.fn>;

describe("EvaluationDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders evaluation detail", async () => {
    getMock.mockResolvedValue({
      evaluation_id: "eval-1",
      agent_id: "support.agent",
      agent_version: "v1.2",
      status: "completed",
      score: 92,
      metrics: { accuracy: 0.92 },
      judge_mode: "llm_judge",
      token_cost: 1200,
      completed_at: "2026-01-01T00:00:00Z",
      started_at: "2026-01-01T00:00:00Z",
      failures: [],
      metadata: {},
    });

    render(
      <MemoryRouter initialEntries={["/governance/evaluations/eval-1"]}>
        <Routes>
          <Route path="/governance/evaluations/:id" element={<EvaluationDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("support.agent")).toBeInTheDocument();
    });
    expect(screen.getByText("llm_judge")).toBeInTheDocument();
  });
});

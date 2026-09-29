import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import AgentConsolePage from "../pages/AgentConsolePage";
import { intelligenceApi } from "../api/intelligence";
import { normalizePosture } from "../types/console";
import { QualityTrendChart } from "../components/QualityTrendChart";
import { InsightCardList } from "../components/InsightCardList";
import { RecommendationCardList } from "../components/RecommendationCardList";

vi.mock("@/auth", () => ({
  useCan: (perm: string) => perm === "intelligence:read" || perm === "intelligence:update",
}));

vi.mock("../api/intelligence", () => ({
  intelligenceApi: {
    getConsole: vi.fn(),
    listRecommendations: vi.fn(),
    getInsight: vi.fn(),
    getInsightExplanation: vi.fn(),
    getQualityAssessmentExplanation: vi.fn(),
    acknowledgeInsight: vi.fn(),
    resolveInsight: vi.fn(),
  },
}));

const consoleFixture = {
  agent_id: "agent-1",
  quality_posture: "degraded",
  quality_explanation_ref: "qa-1",
  top_insights: [{ insight_id: "ins-1", severity: "high", status: "NEW" }],
  top_recommendations: [
    {
      recommendation_id: "rec-1",
      type: "review",
      group: "version_quality_review",
      priority: "high",
    },
  ],
  trend_points: [
    {
      timestamp: "2026-09-01T00:00:00Z",
      posture: "healthy",
      score_delta: null,
      insight_count: 0,
      regression_detected: false,
      agent_version: "1.0.0",
      evaluation_id: "eval-1",
    },
    {
      timestamp: "2026-09-10T00:00:00Z",
      posture: "degraded",
      score_delta: -0.15,
      insight_count: 1,
      regression_detected: true,
      agent_version: "2.0.0",
      evaluation_id: "eval-2",
    },
  ],
  open_insight_count: 1,
  generated_at: "2026-09-24T00:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/intelligence/agents/agent-1/console"]}>
      <Routes>
        <Route path="/intelligence/agents/:agentId/console" element={<AgentConsolePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("normalizePosture", () => {
  it("maps known and unknown values", () => {
    expect(normalizePosture("healthy")).toBe("healthy");
    expect(normalizePosture("RISK_DETECTED")).toBe("risk_detected");
    expect(normalizePosture("blocked")).toBe("unknown");
  });
});

describe("QualityTrendChart", () => {
  it("shows empty state", () => {
    render(<QualityTrendChart points={[]} />);
    expect(screen.getByText(/No historical trend points/i)).toBeInTheDocument();
  });
});

describe("InsightCardList", () => {
  it("renders insight rows without deploy controls", () => {
    render(
      <InsightCardList
        insights={consoleFixture.top_insights}
        onExplain={vi.fn()}
        onAcknowledge={vi.fn()}
        onResolve={vi.fn()}
        canUpdate
      />,
    );
    expect(screen.getByText("ins-1")).toBeInTheDocument();
    expect(screen.queryByText(/deploy/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/approve/i)).not.toBeInTheDocument();
  });
});

describe("RecommendationCardList", () => {
  it("marks recommendations as advisory", () => {
    render(
      <RecommendationCardList recommendations={consoleFixture.top_recommendations} />,
    );
    expect(screen.getByText(/Advisory only/i)).toBeInTheDocument();
    expect(screen.queryByText(/AutoFix/i)).not.toBeInTheDocument();
  });
});

describe("AgentConsolePage", () => {
  beforeEach(() => {
    vi.mocked(intelligenceApi.getConsole).mockResolvedValue(consoleFixture);
    vi.mocked(intelligenceApi.listRecommendations).mockResolvedValue({
      recommendations: [
        {
          recommendation_id: "rec-1",
          explanation: { reason: "Review regression evidence" },
        },
      ],
      count: 1,
    });
  });

  it("loads console projection", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Intelligence Console")).toBeInTheDocument();
    });
    expect(screen.getByText("agent-1")).toBeInTheDocument();
    expect(screen.getByText(/Observe \/ Explain \/ Recommend/i)).toBeInTheDocument();
    expect(screen.getByText(/No approve, reject, deploy/i)).toBeInTheDocument();
    expect(intelligenceApi.getConsole).toHaveBeenCalledWith("agent-1");
  });

  it("falls back when QA explanation is unavailable", async () => {
    vi.mocked(intelligenceApi.getQualityAssessmentExplanation).mockRejectedValue(
      Object.assign(new Error("Assessment not found"), { status: 404 }),
    );
    renderPage();
    await waitFor(() => expect(screen.getByText(/View quality explanation/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText(/View quality explanation/i));
    await waitFor(() => {
      expect(screen.getByText(/Quality explanation unavailable/i)).toBeInTheDocument();
    });
  });

  it("shows API error state", async () => {
    vi.mocked(intelligenceApi.getConsole).mockRejectedValue(new Error("backend down"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Failed to load console/i)).toBeInTheDocument();
    });
    expect(screen.getByText("backend down")).toBeInTheDocument();
  });

  it("shows permission denied for 403", async () => {
    vi.mocked(intelligenceApi.getConsole).mockRejectedValue(
      Object.assign(new Error("Forbidden"), { status: 403 }),
    );
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("403")).toBeInTheDocument();
    });
  });
});

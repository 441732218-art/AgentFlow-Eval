import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TraceTimeline } from "./TraceTimeline";

describe("TraceTimeline", () => {
  it("renders empty state when no steps", () => {
    render(<TraceTimeline steps={[]} />);
    expect(screen.getByText(/No trace steps/i)).toBeInTheDocument();
  });

  it("renders agent and tool steps", () => {
    render(
      <TraceTimeline
        steps={[
          { type: "agent.started", status: "running", timestamp: "2026-01-01T00:00:00Z" },
          { type: "tool.started", tool_name: "trade.search_customer" },
          { type: "agent.completed", duration_ms: 120 },
        ]}
      />,
    );
    expect(screen.getByText("Agent Started")).toBeInTheDocument();
    expect(screen.getByText("Tool Requested")).toBeInTheDocument();
    expect(screen.getByText("trade.search_customer")).toBeInTheDocument();
    expect(screen.getByText("Agent Completed")).toBeInTheDocument();
  });
});

import { describe, it, expect, vi } from "vitest";
import { intelligenceApi } from "./intelligence";
import { apiClient } from "@/api/client";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("intelligenceApi", () => {
  it("calls console endpoint", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { agent_id: "a1", quality_posture: "unknown", top_insights: [] },
    });
    await intelligenceApi.getConsole("a1");
    expect(apiClient.get).toHaveBeenCalledWith(
      "/intelligence/agents/a1/console",
      expect.objectContaining({
        params: expect.objectContaining({ include_trend: true }),
      }),
    );
  });

  it("calls insight explanation endpoint", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { reason: "ok" } });
    await intelligenceApi.getInsightExplanation("ins-1");
    expect(apiClient.get).toHaveBeenCalledWith("/intelligence/insights/ins-1/explanation");
  });

  it("does not expose governance or runtime paths", () => {
    const source = Object.values(intelligenceApi)
      .map((fn) => String(fn))
      .join("\n");
    expect(source).not.toMatch(/governance\/dashboard/);
    expect(source).not.toMatch(/\/runtime\//);
    expect(source).not.toMatch(/deploy/);
  });
});

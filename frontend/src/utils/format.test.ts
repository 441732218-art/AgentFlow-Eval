import { describe, it, expect } from "vitest";
import { formatTokens, formatDuration, getStatusColor, formatDateTime } from "./format";

describe("format utils", () => {
  it("formats token counts", () => {
    expect(formatTokens(500)).toBe("500");
    expect(formatTokens(1500)).toBe("1.5k");
  });

  it("formats durations", () => {
    expect(formatDuration(250)).toBe("250ms");
    expect(formatDuration(1500)).toBe("1.5s");
  });

  it("maps status colors", () => {
    expect(getStatusColor("completed")).toBe("success");
    expect(getStatusColor("failed")).toBe("error");
    expect(getStatusColor("running")).toBe("processing");
    expect(getStatusColor("created")).toBe("default");
  });

  it("handles empty datetime", () => {
    expect(formatDateTime(null)).toBe("-");
    expect(formatDateTime(undefined)).toBe("-");
  });
});

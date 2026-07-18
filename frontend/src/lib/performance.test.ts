import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { debounce, throttle, ROUTE_PREFETCH } from "./performance";

describe("debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("delays invocation until wait elapses", () => {
    const fn = vi.fn();
    const d = debounce(fn, 200);
    d();
    d();
    d();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(200);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("cancel prevents pending call", () => {
    const fn = vi.fn();
    const d = debounce(fn, 100);
    d();
    d.cancel();
    vi.advanceTimersByTime(150);
    expect(fn).not.toHaveBeenCalled();
  });
});

describe("throttle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("limits call frequency", () => {
    const fn = vi.fn();
    const t = throttle(fn, 100);
    t();
    t();
    expect(fn).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(100);
    t();
    expect(fn).toHaveBeenCalledTimes(2);
  });
});

describe("ROUTE_PREFETCH", () => {
  it("exposes lazy importers for main routes", () => {
    expect(typeof ROUTE_PREFETCH.dashboard).toBe("function");
    expect(typeof ROUTE_PREFETCH.tasks).toBe("function");
    expect(typeof ROUTE_PREFETCH.settings).toBe("function");
  });
});

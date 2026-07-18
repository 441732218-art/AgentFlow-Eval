/* (c) 2026 AgentFlow-Eval — small performance helpers */

/**
 * Debounce a function (leading=false, trailing=true).
 */
export function debounce<T extends (...args: never[]) => void>(
  fn: T,
  waitMs: number
): T & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const wrapped = ((...args: Parameters<T>) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  }) as T & { cancel: () => void };
  wrapped.cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };
  return wrapped;
}

/**
 * Throttle a function to at most once per `waitMs`.
 */
export function throttle<T extends (...args: never[]) => void>(
  fn: T,
  waitMs: number
): T {
  let last = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  return ((...args: Parameters<T>) => {
    const now = Date.now();
    const remaining = waitMs - (now - last);
    if (remaining <= 0) {
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      last = now;
      fn(...args);
    } else if (!timer) {
      timer = setTimeout(() => {
        last = Date.now();
        timer = null;
        fn(...args);
      }, remaining);
    }
  }) as T;
}

/**
 * Idle-schedule a callback (falls back to setTimeout).
 */
export function scheduleIdle(cb: () => void, timeout = 1500): void {
  if (typeof window !== "undefined" && "requestIdleCallback" in window) {
    (
      window as Window & {
        requestIdleCallback: (fn: () => void, opts?: { timeout: number }) => number;
      }
    ).requestIdleCallback(cb, { timeout });
  } else {
    setTimeout(cb, Math.min(timeout, 200));
  }
}

/**
 * Prefetch a lazy route module on intent (hover / focus).
 */
export function prefetchRoute(
  importer: () => Promise<unknown>
): void {
  scheduleIdle(() => {
    void importer().catch(() => {
      /* ignore prefetch errors */
    });
  });
}

/** Route module importers for sidebar hover prefetch */
export const ROUTE_PREFETCH = {
  dashboard: () => import("@/dashboard/DashboardPage"),
  traces: () => import("@/traces/TraceExplorerPage"),
  diagnosis: () => import("@/diagnosis/DiagnosisPage"),
  analytics: () => import("@/analytics/AnalyticsPage"),
  monitoring: () => import("@/monitoring/MonitoringPage"),
  tasks: () => import("@/pages/tasks/index"),
  createTask: () => import("@/pages/tasks/create"),
  reports: () => import("@/pages/reports/index"),
  billing: () => import("@/pages/billing/index"),
  plugins: () => import("@/pages/plugins/index"),
  settings: () => import("@/pages/Settings"),
} as const;

/* (c) 2026 AgentFlow-Eval — React Query defaults aligned with backend cache TTLs */
import { QueryClient } from "@tanstack/react-query";

/**
 * Stale / GC times mirror backend multi-layer cache where possible:
 * - task list ~30s → 30s stale
 * - task detail ~5min → 5min stale
 * - dashboard ~1min → 1min stale
 * - settings ~10min → 10min stale
 */
export const QUERY_STALE = {
  taskList: 30_000,
  taskDetail: 5 * 60_000,
  dashboard: 60_000,
  settings: 10 * 60_000,
  report: 2 * 60_000,
  traces: 60_000,
  default: 2 * 60_000,
} as const;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: QUERY_STALE.default,
      gcTime: 15 * 60_000, // keep unused data 15m (was cacheTime in v4)
      retry: 2,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      structuralSharing: true,
    },
    mutations: {
      retry: 1,
    },
  },
});

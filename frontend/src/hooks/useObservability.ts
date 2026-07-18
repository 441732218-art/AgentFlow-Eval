/* (c) 2026 AgentFlow-Eval */
import { useQuery } from "@tanstack/react-query";
import { observabilityApi } from "@/api/endpoints/observability";

export const KPIS_QUERY_KEY = ["observability", "kpis"] as const;
export const SLOW_TASKS_QUERY_KEY = ["observability", "slow-tasks"] as const;

export function useBusinessKpis(days = 7) {
  return useQuery({
    queryKey: [...KPIS_QUERY_KEY, days],
    queryFn: () => observabilityApi.kpis(days),
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });
}

export function useSlowTasks(
  limit = 10,
  source: "auto" | "db" | "memory" = "auto"
) {
  return useQuery({
    queryKey: [...SLOW_TASKS_QUERY_KEY, limit, source],
    queryFn: () => observabilityApi.slowTasks(limit, source),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

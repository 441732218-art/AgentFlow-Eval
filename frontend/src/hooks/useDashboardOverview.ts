import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/api/endpoints/dashboard";

export const DASHBOARD_OVERVIEW_KEY = ["dashboard", "overview"] as const;

export function useDashboardOverview(days = 7) {
  return useQuery({
    queryKey: [...DASHBOARD_OVERVIEW_KEY, days],
    queryFn: () => dashboardApi.overview(days),
    staleTime: 30_000,
    refetchInterval: 45_000,
  });
}

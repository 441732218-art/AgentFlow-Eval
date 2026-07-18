import { useQuery } from "@tanstack/react-query";
import { logsApi, type LogsListParams } from "@/api/endpoints/logs";

export const LOGS_QUERY_KEY = ["logs"] as const;
export const LOGS_STATS_KEY = ["logs", "statistics"] as const;

export function useLogs(params?: LogsListParams) {
  return useQuery({
    queryKey: [...LOGS_QUERY_KEY, params],
    queryFn: () => logsApi.list(params),
    staleTime: 15_000,
    refetchInterval: 20_000,
  });
}

export function useLogStatistics(days = 7) {
  return useQuery({
    queryKey: [...LOGS_STATS_KEY, days],
    queryFn: () => logsApi.statistics(days),
    staleTime: 30_000,
  });
}

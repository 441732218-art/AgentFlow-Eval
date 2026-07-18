import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { traceApi } from "@/api/endpoints/traces";
import type { TraceListParams } from "@/types";

export const TRACES_QUERY_KEY = ["traces"] as const;

export function useTraces(params?: TraceListParams) {
  return useQuery({
    queryKey: [...TRACES_QUERY_KEY, params],
    queryFn: () => traceApi.list(params),
    staleTime: 30_000,
  });
}

export function useTraceDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["trace", id],
    queryFn: () => traceApi.get(id!),
    enabled: !!id,
  });
}

export function useJudgeTrace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: traceApi.judge,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRACES_QUERY_KEY });
    },
  });
}

import { useQuery } from "@tanstack/react-query";
import { diagnosisApi } from "@/api/endpoints/diagnosis";

export const DIAGNOSIS_LIST_KEY = ["diagnosis", "list"] as const;

export function useDiagnosisList(limit = 12) {
  return useQuery({
    queryKey: [...DIAGNOSIS_LIST_KEY, limit],
    queryFn: () => diagnosisApi.list(limit),
    staleTime: 30_000,
  });
}

export function useTaskDiagnosis(taskId: string | undefined) {
  return useQuery({
    queryKey: ["diagnosis", "task", taskId],
    queryFn: () => diagnosisApi.byTask(taskId!),
    enabled: !!taskId,
    staleTime: 20_000,
  });
}

export function useTraceDiagnosis(traceId: string | undefined) {
  return useQuery({
    queryKey: ["diagnosis", "trace", traceId],
    queryFn: () => diagnosisApi.byTrace(traceId!),
    enabled: !!traceId,
  });
}

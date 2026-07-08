import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { taskApi } from "@/api/endpoints/tasks";
import type { TaskListParams, CreateTestSuiteInput } from "@/types";

export const TASKS_QUERY_KEY = ["tasks"] as const;

export function useTasks(params?: TaskListParams) {
  return useQuery({
    queryKey: [...TASKS_QUERY_KEY, params],
    queryFn: () => taskApi.list(params),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useTaskDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["task", id],
    queryFn: () => taskApi.get(id!),
    enabled: !!id,
    retry: (_failureCount, error) => {
      return (error as any)?.response?.status !== 404;
    },
  });
}

export function useTaskReport(id: string | undefined) {
  return useQuery({
    queryKey: ["task-report", id],
    queryFn: () => taskApi.getReport(id!),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.delete,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
      queryClient.removeQueries({ queryKey: ["task", id] });
    },
  });
}

export function useExecuteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.execute,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["task", id] });
    },
  });
}

export function useCreateTestSuites(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (suites: CreateTestSuiteInput[]) =>
      taskApi.createTestSuites(taskId, suites),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });
}


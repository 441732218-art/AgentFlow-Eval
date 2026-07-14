import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { taskApi } from "@/api/endpoints/tasks";
import type { TaskListParams, CreateTestSuiteInput, Task, TaskReport } from "@/types";

export const TASKS_QUERY_KEY = ["tasks"] as const;

export function useTasks(params?: TaskListParams) {
  return useQuery({
    queryKey: [...TASKS_QUERY_KEY, params],
    queryFn: () => taskApi.list(params),
    staleTime: 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useTaskDetail(id: string | undefined, options?: { refetchInterval?: number | false; enabled?: boolean }) {
  return useQuery<Task, Error>({
    queryKey: ["task", id],
    queryFn: () => taskApi.get(id!),
    enabled: !!id,
    retry: (_failureCount, error) => {
      return (error as any)?.response?.status !== 404;
    },
    ...options,
  });
}

export function useTaskReport(id: string | undefined, options?: { refetchInterval?: number | false; enabled?: boolean }) {
  return useQuery<TaskReport, Error>({
    queryKey: ["task-report", id],
    queryFn: () => taskApi.getReport(id!),
    enabled: !!id,
    ...options,
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

export function useCancelTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.cancel,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["task", id] });
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
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
      queryClient.invalidateQueries({ queryKey: ["task-report", taskId] });
    },
  });
}

export function useUploadTestSuites(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => taskApi.uploadTestSuites(taskId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["task-report", taskId] });
    },
  });
}

export function useArchiveTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.archive,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["task", id] });
      queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
    },
  });
}


import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import { taskApi } from "@/api/endpoints/tasks";
import { dashboardApi } from "@/api/endpoints/dashboard";
import type { TaskListParams, CreateTestSuiteInput, Task, TaskReport } from "@/types";
import { QUERY_STALE } from "@/lib/query-client";

export const TASKS_QUERY_KEY = ["tasks"] as const;
export const DASHBOARD_QUERY_KEY = ["dashboard", "stats"] as const;

function invalidateTaskRelated(queryClient: ReturnType<typeof useQueryClient>, id?: string) {
  queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
  queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEY });
  if (id) {
    queryClient.invalidateQueries({ queryKey: ["task", id] });
  }
}

export function useTasks(params?: TaskListParams) {
  return useQuery({
    queryKey: [...TASKS_QUERY_KEY, params],
    queryFn: () => taskApi.list(params),
    // Align with backend list cache TTL (~30s)
    staleTime: QUERY_STALE.taskList,
    placeholderData: keepPreviousData,
  });
}

export function useDashboardStats(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: DASHBOARD_QUERY_KEY,
    queryFn: () => dashboardApi.stats(),
    staleTime: QUERY_STALE.dashboard,
    ...options,
  });
}

export function useTaskDetail(id: string | undefined, options?: { refetchInterval?: number | false; enabled?: boolean }) {
  return useQuery<Task, Error>({
    queryKey: ["task", id],
    queryFn: () => taskApi.get(id!),
    enabled: !!id,
    staleTime: QUERY_STALE.taskDetail,
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
    staleTime: QUERY_STALE.report,
    ...options,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.create,
    onSuccess: () => {
      invalidateTaskRelated(queryClient);
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.delete,
    onSuccess: (_data, id) => {
      invalidateTaskRelated(queryClient, id);
      queryClient.removeQueries({ queryKey: ["task", id] });
    },
  });
}

export function useExecuteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.execute,
    onSuccess: (_data, id) => {
      invalidateTaskRelated(queryClient, id);
      // Refresh quota strip after a successful run is queued
      queryClient.invalidateQueries({ queryKey: ["billing", "quota"] });
      queryClient.invalidateQueries({ queryKey: ["billing", "usage"] });
    },
  });
}

export function useCancelTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: taskApi.cancel,
    onSuccess: (_data, id) => {
      invalidateTaskRelated(queryClient, id);
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
      invalidateTaskRelated(queryClient, id);
    },
  });
}


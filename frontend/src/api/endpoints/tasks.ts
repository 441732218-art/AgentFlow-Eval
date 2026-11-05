import { apiClient } from "../client";
import type {
  Task,
  TaskCreate,
  PaginatedResponse,
  TaskReport,
  ExecuteTaskResponse,
  CreateTestSuitesResponse,
  CreateTestSuiteInput,
} from "@/types";

/** Response from POST /tasks/{id}/test-suites/import-csv */
export interface ImportCsvTestSuitesResponse {
  task_id: string;
  created: number;
  skipped: number;
  filename: string | null;
  message: string;
}

export const taskApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    status?: string;
    include_archived?: boolean;
  }) =>
    apiClient.get<PaginatedResponse<Task>>("/tasks", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Task>(`/tasks/${id}`).then((r) => r.data),

  create: (data: TaskCreate) =>
    apiClient.post<Task>("/tasks", data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/tasks/${id}`).then((r) => r.data),

  execute: (id: string) =>
    apiClient.post<ExecuteTaskResponse>(`/tasks/${id}/execute`).then((r) => r.data),

  createTestSuites: (taskId: string, suites: CreateTestSuiteInput[]) =>
    apiClient
      .post<CreateTestSuitesResponse>(`/tasks/${taskId}/test-suites`, suites)
      .then((r) => r.data),

  uploadTestSuites: (taskId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<CreateTestSuitesResponse & { filename?: string; message?: string }>(
        `/tasks/${taskId}/test-suites/upload`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } }
      )
      .then((r) => r.data);
  },

  importCsvTestSuites: (taskId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    // Let the client/runtime set multipart Content-Type + boundary (do not hardcode).
    return apiClient
      .post<ImportCsvTestSuitesResponse>(
        `/tasks/${taskId}/test-suites/import-csv`,
        form
      )
      .then((r) => r.data);
  },

  getReport: (id: string) =>
    apiClient.get<TaskReport>(`/reports/${id}`).then((r) => r.data),

  cancel: (id: string) =>
    apiClient.post(`/tasks/${id}/cancel`).then((r) => r.data),

  archive: (id: string) =>
    apiClient.post(`/tasks/${id}/archive`).then((r) => r.data),

  unarchive: (id: string) =>
    apiClient.post(`/tasks/${id}/unarchive`).then((r) => r.data),
};

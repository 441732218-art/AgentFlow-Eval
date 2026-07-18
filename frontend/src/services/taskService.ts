/* (c) 2026 AgentFlow-Eval
 * @deprecated Use `@/api/endpoints/tasks` (`taskApi`) instead.
 * Kept as a thin compatibility shim for any external imports.
 */
import { taskApi } from "@/api/endpoints/tasks";
import type { Task, TaskCreatePayload, TaskListResponse } from "../types";

/** @deprecated Prefer `taskApi` from `@/api` */
export const taskService = {
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    include_archived?: boolean;
  }): Promise<TaskListResponse> {
    return taskApi.list(params) as Promise<TaskListResponse>;
  },

  async create(payload: TaskCreatePayload): Promise<Task> {
    return taskApi.create(payload as never) as Promise<Task>;
  },

  async getById(id: string): Promise<Task> {
    return taskApi.get(id);
  },

  async delete(id: string): Promise<void> {
    await taskApi.delete(id);
  },

  async execute(id: string): Promise<{ task_id: string; status: string }> {
    return taskApi.execute(id) as Promise<{ task_id: string; status: string }>;
  },

  async getReport(id: string) {
    return taskApi.getReport(id);
  },

  async archive(id: string) {
    return taskApi.archive(id);
  },
};

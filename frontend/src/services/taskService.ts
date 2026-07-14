/* (c) 2026 AgentFlow-Eval */
/* 兼容层：委托给 taskApi（React Query hooks 为推荐用法） */

import { taskApi } from "@/api/endpoints/tasks";
import type { Task, TaskCreatePayload, TaskListResponse } from "../types";

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
    return taskApi.create(payload);
  },

  async getById(id: string): Promise<Task> {
    return taskApi.get(id);
  },

  async delete(id: string): Promise<void> {
    await taskApi.delete(id);
  },

  async execute(id: string): Promise<{ task_id: string; status: string }> {
    return taskApi.execute(id);
  },

  async getReport(id: string) {
    return taskApi.getReport(id);
  },

  async archive(id: string) {
    return taskApi.archive(id);
  },

  async uploadTestSuites(taskId: string, file: File) {
    return taskApi.uploadTestSuites(taskId, file);
  },
};

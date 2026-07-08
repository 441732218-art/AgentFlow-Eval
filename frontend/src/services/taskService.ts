/* (c) 2026 AgentFlow-Eval */

import api from "./api";
import type { Task, TaskCreatePayload, TaskListResponse } from "../types";

export const taskService = {
  /** 获取评测任务列表 */
  async list(params?: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Promise<TaskListResponse> {
    const { data } = await api.get<TaskListResponse>("/tasks", { params });
    return data;
  },

  /** 创建评测任务 */
  async create(payload: TaskCreatePayload): Promise<Task> {
    const { data } = await api.post<Task>("/tasks", payload);
    return data;
  },

  /** 获取单个任务详情 */
  async getById(id: string): Promise<Task> {
    const { data } = await api.get<Task>(`/tasks/${id}`);
    return data;
  },

  /** 删除任务 */
  async delete(id: string): Promise<void> {
    await api.delete(`/tasks/${id}`);
  },

  /** 触发任务执行 */
  async execute(id: string): Promise<{ task_id: string; status: string }> {
    const { data } = await api.post(`/tasks/${id}/execute`);
    return data;
  },

  /** 获取任务报告 */
  async getReport(id: string) {
    const { data } = await api.get(`/reports/${id}`);
    return data;
  },
};

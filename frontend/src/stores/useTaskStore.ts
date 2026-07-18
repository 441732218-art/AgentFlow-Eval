/* (c) 2026 AgentFlow-Eval */

import { create } from "zustand";
import type { Task, TaskCreatePayload, TaskListResponse, TaskReport } from "../types";
import { taskApi } from "@/api/endpoints/tasks";

interface TaskState {
  tasks: Task[];
  total: number;
  currentPage: number;
  loading: boolean;
  currentTask: Task | null;
  currentReport: TaskReport | null;

  fetchTasks: (page?: number, status?: string) => Promise<void>;
  createTask: (payload: TaskCreatePayload) => Promise<Task>;
  fetchTask: (id: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  executeTask: (id: string) => Promise<void>;
  fetchReport: (id: string) => Promise<void>;
  reset: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  total: 0,
  currentPage: 1,
  loading: false,
  currentTask: null,
  currentReport: null,

  fetchTasks: async (page = 1, status?: string) => {
    set({ loading: true });
    try {
      const res = (await taskApi.list({
        page,
        page_size: 20,
        status,
      })) as TaskListResponse;
      set({ tasks: res.items, total: res.total, currentPage: page });
    } finally {
      set({ loading: false });
    }
  },

  createTask: async (payload: TaskCreatePayload) => {
    const task = (await taskApi.create(payload as never)) as Task;
    set((state) => ({ tasks: [task, ...state.tasks], total: state.total + 1 }));
    return task;
  },

  fetchTask: async (id: string) => {
    set({ loading: true });
    try {
      const task = (await taskApi.get(id)) as Task;
      set({ currentTask: task });
    } finally {
      set({ loading: false });
    }
  },

  deleteTask: async (id: string) => {
    await taskApi.delete(id);
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
      total: state.total - 1,
    }));
  },

  executeTask: async (id: string) => {
    await taskApi.execute(id);
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, status: "running" as const } : t,
      ),
    }));
  },

  fetchReport: async (id: string) => {
    const report = (await taskApi.getReport(id)) as TaskReport;
    set({ currentReport: report });
  },

  reset: () => set({ tasks: [], total: 0, currentPage: 1, loading: false, currentTask: null, currentReport: null }),
}));

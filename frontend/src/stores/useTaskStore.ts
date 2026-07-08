/* (c) 2026 AgentFlow-Eval */

import { create } from "zustand";
import type { Task, TaskCreatePayload, TaskListResponse, TaskReport } from "../types";
import { taskService } from "../services/taskService";

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
      const res: TaskListResponse = await taskService.list({ page, page_size: 20, status });
      set({ tasks: res.items, total: res.total, currentPage: page });
    } finally {
      set({ loading: false });
    }
  },

  createTask: async (payload: TaskCreatePayload) => {
    const task = await taskService.create(payload);
    set((state) => ({ tasks: [task, ...state.tasks], total: state.total + 1 }));
    return task;
  },

  fetchTask: async (id: string) => {
    set({ loading: true });
    try {
      const task = await taskService.getById(id);
      set({ currentTask: task });
    } finally {
      set({ loading: false });
    }
  },

  deleteTask: async (id: string) => {
    await taskService.delete(id);
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
      total: state.total - 1,
    }));
  },

  executeTask: async (id: string) => {
    await taskService.execute(id);
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, status: "running" as const } : t,
      ),
    }));
  },

  fetchReport: async (id: string) => {
    const report = await taskService.getReport(id);
    set({ currentReport: report });
  },

  reset: () => set({ tasks: [], total: 0, currentPage: 1, loading: false, currentTask: null, currentReport: null }),
}));

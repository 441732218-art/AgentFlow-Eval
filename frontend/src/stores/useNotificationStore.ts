/* Global activity / notification store with status-change detection */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Task } from "@/types";

export interface ActivityEvent {
  id: string;
  taskId: string;
  taskName: string;
  status: string;
  prevStatus?: string;
  message: string;
  at: string;
  read: boolean;
}

interface NotificationState {
  events: ActivityEvent[];
  /** last known status per task id (for change detection) */
  statusMap: Record<string, string>;
  /** last successful poll ISO time */
  lastPolledAt: string | null;
  /** transport mode for UI badge */
  transport: "ws" | "poll" | "idle";
  setTransport: (t: "ws" | "poll" | "idle") => void;
  /** @param seedOnly when true, only fill statusMap (no events / first poll) */
  ingestTasks: (tasks: Task[], seedOnly?: boolean) => ActivityEvent[];
  markRead: (id: string) => void;
  markAllRead: () => void;
  clear: () => void;
  unreadCount: () => number;
}

function headline(task: Task, prev?: string): string {
  const name = task.name;
  switch (task.status) {
    case "completed":
      return prev ? `任务「${name}」已完成` : `任务「${name}」已完成`;
    case "failed":
      return `任务「${name}」执行失败`;
    case "timeout":
      return `任务「${name}」超时`;
    case "cancelled":
      return `任务「${name}」已取消`;
    case "running":
      return prev === "queued" || prev === "created"
        ? `任务「${name}」开始运行`
        : `任务「${name}」进行中`;
    case "queued":
      return `任务「${name}」已入队`;
    case "judging":
      return `任务「${name}」正在评分`;
    case "created":
      return `新任务「${name}」待执行`;
    default:
      return `任务「${name}」状态 → ${task.status}`;
  }
}

const TERMINAL_TOAST = new Set(["completed", "failed", "timeout", "cancelled"]);
const LIVE = new Set(["running", "queued", "judging", "waiting_tool"]);

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      events: [],
      statusMap: {},
      lastPolledAt: null,
      transport: "idle",
      setTransport: (t) => set({ transport: t }),

      ingestTasks: (tasks, seedOnly = false) => {
        const prevMap = { ...get().statusMap };
        const nextMap = { ...prevMap };
        const fresh: ActivityEvent[] = [];
        const now = new Date().toISOString();

        for (const task of tasks) {
          const prev = prevMap[task.id];
          nextMap[task.id] = task.status;

          if (seedOnly || prev === undefined) {
            // first sighting or cold start — only snapshot, no flood
            continue;
          }

          if (prev !== task.status) {
            const ev: ActivityEvent = {
              id: `${task.id}:${task.status}:${task.updated_at || now}`,
              taskId: task.id,
              taskName: task.name,
              status: task.status,
              prevStatus: prev,
              message: headline(task, prev),
              at: task.updated_at || now,
              read: false,
            };
            fresh.push(ev);
          }
        }

        if (fresh.length === 0) {
          set({ statusMap: nextMap, lastPolledAt: now });
          return [];
        }

        set((state) => {
          const ids = new Set(state.events.map((e) => e.id));
          const merged = [...fresh.filter((e) => !ids.has(e.id)), ...state.events].slice(
            0,
            80
          );
          return {
            events: merged,
            statusMap: nextMap,
            lastPolledAt: now,
          };
        });

        return fresh;
      },

      markRead: (id) =>
        set((s) => ({
          events: s.events.map((e) => (e.id === id ? { ...e, read: true } : e)),
        })),

      markAllRead: () =>
        set((s) => ({
          events: s.events.map((e) => ({ ...e, read: true })),
        })),

      clear: () => set({ events: [] }),

      unreadCount: () => get().events.filter((e) => !e.read).length,
    }),
    {
      name: "agentflow_notifications",
      partialize: (s) => ({
        events: s.events.slice(0, 40),
        statusMap: s.statusMap,
        lastPolledAt: s.lastPolledAt,
        // transport is runtime-only
      }),
    }
  )
);

export { TERMINAL_TOAST, LIVE };

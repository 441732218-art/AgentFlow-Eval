/* Live activity: WebSocket primary + polling fallback */

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { taskApi } from "@/api/endpoints/tasks";
import { TASKS_QUERY_KEY } from "@/hooks/useTasks";
import { useNotificationStore, LIVE } from "@/stores/useNotificationStore";
import type { Task } from "@/types";

const SETTINGS_KEY = "agentflow_settings";

function readPollIntervalMs(): number {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return 5000;
    const parsed = JSON.parse(raw) as { pollIntervalSec?: number };
    const sec = Number(parsed.pollIntervalSec) || 5;
    return Math.min(60, Math.max(1, sec)) * 1000;
  } catch {
    return 5000;
  }
}

function readApiKey(): string {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return "";
    return ((JSON.parse(raw) as { apiKey?: string }).apiKey || "").trim(); // kept in sync with settings-storage
  } catch {
    return "";
  }
}

function toastFor(status: string, message: string) {
  if (status === "completed") toast.success(message);
  else if (status === "failed" || status === "timeout") toast.error(message);
  else if (status === "cancelled") toast.message(message);
  else if (LIVE.has(status)) toast.info(message);
  else toast(message);
}

function resolveWsUrl(): string {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  // Absolute http(s) base → convert to ws(s)
  if (base.startsWith("http://") || base.startsWith("https://")) {
    const u = new URL(base.replace(/\/$/, "") + "/ws/activities");
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    return u.toString();
  }
  // Relative → use current host
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const path = base.endsWith("/")
    ? `${base}ws/activities`
    : `${base}/ws/activities`;
  return `${proto}//${window.location.host}${path}`;
}

function eventToSyntheticTask(ev: {
  task_id: string;
  task_name: string;
  status: string;
  at?: string;
}): Task {
  return {
    id: ev.task_id,
    name: ev.task_name || ev.task_id,
    description: "",
    status: ev.status as Task["status"],
    agent_config: {},
    celery_task_id: null,
    created_at: ev.at || new Date().toISOString(),
    updated_at: ev.at || new Date().toISOString(),
    test_suite_count: 0,
  };
}

/**
 * Mount once under MainLayout.
 * Prefer WebSocket; fall back to HTTP polling when disconnected.
 */
export function useActivityWatcher(enabled = true) {
  const queryClient = useQueryClient();
  const ingestTasks = useNotificationStore((s) => s.ingestTasks);
  const setTransport = useNotificationStore((s) => s.setTransport);
  const primed = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    const applyTasks = (tasks: Task[], seedOnly: boolean) => {
      const fresh = ingestTasks(tasks, seedOnly);
      if (!seedOnly) {
        for (const ev of fresh) {
          if (ev.prevStatus) toastFor(ev.status, ev.message);
        }
        queryClient.invalidateQueries({ queryKey: TASKS_QUERY_KEY });
      }
    };

    const pollOnce = async (seedOnly = false) => {
      try {
        const data = await taskApi.list({ page: 1, page_size: 50 });
        if (cancelled) return;
        applyTasks(data.items || [], seedOnly);
      } catch {
        /* silent */
      }
    };

    const schedulePoll = (delay?: number) => {
      if (pollTimer.current) clearTimeout(pollTimer.current);
      pollTimer.current = setTimeout(async () => {
        if (cancelled) return;
        // When WS is open, poll less aggressively as soft sync
        const wsOpen = wsRef.current?.readyState === WebSocket.OPEN;
        await pollOnce(false);
        if (!cancelled) {
          schedulePoll(wsOpen ? Math.max(readPollIntervalMs() * 3, 15000) : readPollIntervalMs());
        }
      }, delay ?? readPollIntervalMs());
    };

    const connectWs = () => {
      if (cancelled) return;
      try {
        const url = resolveWsUrl();
        const key = readApiKey();
        // API key as query if needed (WS can't always set headers)
        const full = key ? `${url}${url.includes("?") ? "&" : "?"}api_key=${encodeURIComponent(key)}` : url;
        const ws = new WebSocket(full);
        wsRef.current = ws;

        ws.onopen = () => {
          if (cancelled) return;
          setTransport("ws");
          // Prime once via HTTP so statusMap is warm
          if (!primed.current) {
            void pollOnce(true).then(() => {
              primed.current = true;
            });
          }
          // Soft poll backup while WS is up
          schedulePoll(20000);
        };

        ws.onmessage = (msg) => {
          try {
            const data = JSON.parse(msg.data as string) as {
              type?: string;
              task_id?: string;
              task_name?: string;
              status?: string;
              prev_status?: string;
              at?: string;
            };
            if (data.type === "ping") {
              ws.send(JSON.stringify({ type: "pong" }));
              return;
            }
            if (data.type === "hello" || data.type === "pong") return;
            if (data.type === "task_status" && data.task_id && data.status) {
              if (!primed.current) {
                // ensure map exists
                primed.current = true;
              }
              const synthetic = eventToSyntheticTask({
                task_id: data.task_id,
                task_name: data.task_name || data.task_id,
                status: data.status,
                at: data.at,
              });
              // Force prev status into map so ingest detects change
              const store = useNotificationStore.getState();
              if (data.prev_status && !store.statusMap[data.task_id]) {
                useNotificationStore.setState({
                  statusMap: {
                    ...store.statusMap,
                    [data.task_id]: data.prev_status,
                  },
                });
              } else if (data.prev_status) {
                useNotificationStore.setState({
                  statusMap: {
                    ...store.statusMap,
                    [data.task_id]: data.prev_status,
                  },
                });
              }
              applyTasks([synthetic], false);
            }
          } catch {
            /* ignore bad frames */
          }
        };

        ws.onerror = () => {
          /* onclose will handle */
        };

        ws.onclose = () => {
          wsRef.current = null;
          if (cancelled) return;
          setTransport("poll");
          // Fallback to faster polling
          if (!primed.current) {
            void pollOnce(true).then(() => {
              primed.current = true;
              schedulePoll(800);
            });
          } else {
            schedulePoll(1000);
          }
          reconnectTimer.current = setTimeout(connectWs, 4000);
        };
      } catch {
        setTransport("poll");
        void pollOnce(!primed.current).then(() => {
          primed.current = true;
          schedulePoll();
        });
      }
    };

    // Start WS; poll as fallback
    connectWs();

    const onVisibility = () => {
      if (document.visibilityState === "visible" && !cancelled) {
        void pollOnce(false);
      }
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      cancelled = true;
      document.removeEventListener("visibilitychange", onVisibility);
      if (pollTimer.current) clearTimeout(pollTimer.current);
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      try {
        wsRef.current?.close();
      } catch {
        /* ignore */
      }
      wsRef.current = null;
    };
  }, [enabled, ingestTasks, queryClient, setTransport]);
}

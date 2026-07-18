/* (c) 2026 AgentFlow-Eval */

import dayjs from "dayjs";

/** 格式化日期时间 */
export function formatDateTime(date: string | null | undefined): string {
  if (!date) return "-";
  return dayjs(date).format("YYYY-MM-DD HH:mm:ss");
}

/** 格式化 Token 数量 */
export function formatTokens(count: number): string {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k`;
  }
  return String(count);
}

/** 格式化响应时间 */
export function formatDuration(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}

/** 获取状态对应的颜色 */
export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    pending: "default",
    created: "default",
    queued: "warning",
    running: "processing",
    waiting_tool: "warning",
    judging: "processing",
    completed: "success",
    failed: "error",
    cancelled: "default",
    timeout: "error",
    success: "success",
  };
  return map[status] || "default";
}

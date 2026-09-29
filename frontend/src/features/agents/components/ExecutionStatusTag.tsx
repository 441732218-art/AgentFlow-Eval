import { Tag } from "antd";

const statusColor: Record<string, string> = {
  SUCCESS: "success",
  COMPLETED: "success",
  FAILED: "error",
  RUNNING: "processing",
  PENDING: "default",
  CANCELLED: "warning",
};

export function ExecutionStatusTag({ status }: { status: string }) {
  const normalized = (status || "UNKNOWN").toUpperCase();
  return <Tag color={statusColor[normalized] ?? "default"}>{normalized}</Tag>;
}

export function formatDurationMs(value?: number | null, durationSeconds?: number | null): string {
  if (value != null && value >= 0) {
    if (value < 1000) return `${value} ms`;
    return `${(value / 1000).toFixed(2)} s`;
  }
  if (durationSeconds != null && durationSeconds >= 0) {
    if (durationSeconds < 1) return `${Math.round(durationSeconds * 1000)} ms`;
    return `${durationSeconds.toFixed(2)} s`;
  }
  return "—";
}

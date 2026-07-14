import { Tag } from "antd";

const MAP: Record<string, { color: string; label: string }> = {
  created: { color: "default", label: "Created" },
  queued: { color: "warning", label: "Queued" },
  running: { color: "processing", label: "Running" },
  waiting_tool: { color: "warning", label: "Waiting Tool" },
  judging: { color: "processing", label: "Judging" },
  completed: { color: "success", label: "Completed" },
  failed: { color: "error", label: "Failed" },
  cancelled: { color: "default", label: "Cancelled" },
  timeout: { color: "error", label: "Timeout" },
  partial: { color: "orange", label: "Partial" },
  success: { color: "success", label: "Success" },
};

export function StatusBadge({ status }: { status: string }) {
  const m = MAP[status] || { color: "default", label: status };
  return (
    <Tag
      color={m.color}
      style={{
        margin: 0,
        borderRadius: 6,
        fontWeight: 600,
        letterSpacing: "0.01em",
      }}
    >
      {m.label}
    </Tag>
  );
}

export function OwnerBadge({ owner }: { owner?: string | null }) {
  const o = owner || "anonymous";
  const isAdmin = o === "admin";
  return (
    <Tag color={isAdmin ? "gold" : "processing"} style={{ margin: 0, borderRadius: 6 }}>
      {o}
    </Tag>
  );
}

import { Tag } from "antd";
import type { AgentSummary } from "../types/agent";

const lifecycleColor: Record<string, string> = {
  ACTIVE: "success",
  RETIRED: "default",
  DEPRECATED: "warning",
};

export function AgentStatus({ agent }: { agent: Pick<AgentSummary, "enabled" | "lifecycle_status"> }) {
  const lifecycle = agent.lifecycle_status ?? (agent.enabled ? "ACTIVE" : "RETIRED");
  return (
    <Tag color={agent.enabled ? "green" : "default"}>
      {agent.enabled ? "Enabled" : "Disabled"}
      {lifecycle ? ` · ${lifecycle}` : ""}
    </Tag>
  );
}

export function LifecycleTag({ status }: { status?: string }) {
  if (!status) return null;
  return <Tag color={lifecycleColor[status] ?? "processing"}>{status}</Tag>;
}

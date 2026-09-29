import { Tag } from "antd";
import type { AgentDeployment } from "../types/agent";

const statusColor: Record<string, string> = {
  ACTIVE: "success",
  INACTIVE: "default",
  ROLLBACK: "warning",
};

export function DeploymentStatus({ deployment }: { deployment: AgentDeployment }) {
  return (
    <Tag color={statusColor[deployment.status] ?? "processing"}>{deployment.status}</Tag>
  );
}

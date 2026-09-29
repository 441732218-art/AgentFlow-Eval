import { Timeline, Typography, Tag, Empty } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ToolOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import type { TraceStep } from "../types/agent";
import { formatDateTime } from "@/utils/format";

const { Text } = Typography;

function stepLabel(step: TraceStep): string {
  const type = step.type ?? "";
  if (type.includes("agent.started") || type === "agent.started") return "Agent Started";
  if (type.includes("agent.completed") || type === "agent.completed") return "Agent Completed";
  if (type.includes("agent.failed") || type === "agent.failed") return "Agent Failed";
  if (type.includes("tool.started") || type.includes("tool.requested")) return "Tool Requested";
  if (type.includes("tool.completed") || type.includes("tool.executed")) return "Tool Completed";
  if (type.includes("tool.failed")) return "Tool Failed";
  if (type.includes("permission.denied")) return "Permission Denied";
  if (type.includes("execution.started")) return "Execution Started";
  if (type.includes("execution.completed")) return "Execution Completed";
  if (type.includes("execution.failed")) return "Execution Failed";
  return type || "Step";
}

function stepIcon(step: TraceStep) {
  const type = step.type ?? "";
  if (type.includes("failed") || step.status === "failed" || step.status === "denied") {
    return <CloseCircleOutlined style={{ color: "#ff4d4f" }} />;
  }
  if (type.includes("tool")) return <ToolOutlined style={{ color: "#1677ff" }} />;
  if (type.includes("agent")) return <RobotOutlined style={{ color: "#52c41a" }} />;
  if (step.status === "running") return <LoadingOutlined style={{ color: "#1677ff" }} />;
  return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
}

export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  if (!steps.length) {
    return (
      <Empty
        description="No trace steps recorded for this execution."
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <Timeline
      mode="left"
      items={steps.map((step, index) => ({
        key: `${step.type}-${index}`,
        dot: stepIcon(step),
        label: step.timestamp ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatDateTime(step.timestamp)}
          </Text>
        ) : undefined,
        children: (
          <div>
            <Text strong>{stepLabel(step)}</Text>
            {step.tool_name ? (
              <div>
                <Tag>{step.tool_name}</Tag>
              </div>
            ) : null}
            {step.status ? (
              <div>
                <Text type="secondary">Status: {step.status}</Text>
              </div>
            ) : null}
            {step.duration_ms != null ? (
              <div>
                <Text type="secondary">Duration: {step.duration_ms} ms</Text>
              </div>
            ) : null}
          </div>
        ),
      }))}
    />
  );
}

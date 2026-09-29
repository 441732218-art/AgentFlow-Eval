import { Tag } from "antd";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  QuestionCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import type { QualityPosture } from "../types/console";
import { normalizePosture } from "../types/console";

export function postureTag(posture: string | null | undefined) {
  const value = normalizePosture(posture);
  switch (value) {
    case "healthy":
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          healthy
        </Tag>
      );
    case "degraded":
      return (
        <Tag icon={<WarningOutlined />} color="warning">
          degraded
        </Tag>
      );
    case "risk_detected":
      return (
        <Tag icon={<ExclamationCircleOutlined />} color="error">
          risk_detected
        </Tag>
      );
    default:
      return (
        <Tag icon={<QuestionCircleOutlined />}>
          {(posture as QualityPosture) || "unknown"}
        </Tag>
      );
  }
}

import { Tag } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  MinusCircleOutlined,
} from "@ant-design/icons";

type Props = {
  decision: string | null | undefined;
};

export function DecisionBadge({ decision }: Props) {
  const value = (decision ?? "UNKNOWN").toUpperCase();
  if (value === "APPROVED" || value === "APPROVE" || value === "PASS") {
    return (
      <Tag icon={<CheckCircleOutlined />} color="success">
        {value === "PASS" ? "PASS" : "APPROVED"}
      </Tag>
    );
  }
  if (value === "REJECTED" || value === "REJECT" || value === "FAIL") {
    return (
      <Tag icon={<CloseCircleOutlined />} color="error">
        {value === "FAIL" ? "FAIL" : "REJECTED"}
      </Tag>
    );
  }
  if (value === "WARNING") {
    return (
      <Tag icon={<ExclamationCircleOutlined />} color="warning">
        WARNING
      </Tag>
    );
  }
  return (
    <Tag icon={<MinusCircleOutlined />} color="default">
      {value}
    </Tag>
  );
}

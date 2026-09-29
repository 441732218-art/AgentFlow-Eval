import { Space, Typography } from "antd";
import { RobotOutlined } from "@ant-design/icons";
import { postureTag } from "./postureTag";

const { Text, Paragraph } = Typography;

type Props = {
  agentId: string;
  posture: string;
  openInsightCount: number;
  generatedAt: string | null;
};

export function AgentHeader({ agentId, posture, openInsightCount, generatedAt }: Props) {
  return (
    <Space direction="vertical" size={4} style={{ width: "100%" }}>
      <Space wrap>
        <RobotOutlined />
        <Text strong style={{ fontSize: 18 }}>
          Intelligence Console
        </Text>
        <Text code>{agentId}</Text>
        {postureTag(posture)}
      </Space>
      <Paragraph type="secondary" style={{ marginBottom: 0 }}>
        Open insights: {openInsightCount}
        {generatedAt ? ` · Generated ${generatedAt}` : null}
        {" · Observe / Explain / Recommend only"}
      </Paragraph>
    </Space>
  );
}

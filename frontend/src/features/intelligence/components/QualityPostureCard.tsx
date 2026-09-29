import { Alert, Button, Card, Space, Typography } from "antd";
import { postureTag } from "./postureTag";

const { Text, Paragraph } = Typography;

type Props = {
  posture: string;
  explanationRef: string | null;
  loadingExplain?: boolean;
  explainError?: string | null;
  explainSummary?: string | null;
  onExplain: () => void;
};

export function QualityPostureCard({
  posture,
  explanationRef,
  loadingExplain,
  explainError,
  explainSummary,
  onExplain,
}: Props) {
  return (
    <Card title="Quality posture" className="ic-panel" size="small">
      <Space direction="vertical" style={{ width: "100%" }}>
        <div>
          <Text type="secondary">Current posture </Text>
          {postureTag(posture)}
        </div>
        {explanationRef ? (
          <Button size="small" loading={loadingExplain} onClick={onExplain}>
            View quality explanation
          </Button>
        ) : (
          <Text type="secondary">No quality assessment reference available.</Text>
        )}
        {explainError ? (
          <Alert
            type="warning"
            showIcon
            message="Quality explanation unavailable"
            description={explainError}
          />
        ) : null}
        {explainSummary ? (
          <Paragraph style={{ marginBottom: 0 }}>{explainSummary}</Paragraph>
        ) : null}
      </Space>
    </Card>
  );
}

import { Card, Progress, Space, Typography } from "antd";

const { Text } = Typography;

type Props = {
  label: string;
  score: number | null | undefined;
  suffix?: string;
};

export function GovernanceScoreCard({ label, score, suffix = "%" }: Props) {
  const value = score != null ? Math.max(0, Math.min(100, score)) : null;
  return (
    <Card className="ic-panel" size="small">
      <Space direction="vertical" size={4} style={{ width: "100%" }}>
        <Text type="secondary">{label}</Text>
        {value != null ? (
          <>
            <Text strong style={{ fontSize: 24 }}>
              {value}
              {suffix}
            </Text>
            <Progress percent={value} showInfo={false} strokeColor="var(--af-accent)" />
          </>
        ) : (
          <Text>—</Text>
        )}
      </Space>
    </Card>
  );
}

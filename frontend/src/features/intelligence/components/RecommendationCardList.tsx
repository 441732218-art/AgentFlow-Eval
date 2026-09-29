import { Card, Empty, List, Tag, Typography } from "antd";
import type { RecommendationSummaryRow } from "../types/console";

const { Text, Paragraph } = Typography;

type Props = {
  recommendations: RecommendationSummaryRow[];
  details?: Array<{
    recommendation_id: string;
    explanation?: { reason?: string } | null;
  }>;
};

export function RecommendationCardList({ recommendations, details = [] }: Props) {
  if (!recommendations.length) {
    return (
      <Card title="Advisory recommendations" className="ic-panel" size="small">
        <Empty description="No recommendations" />
      </Card>
    );
  }

  const reasonById = new Map(
    details.map((item) => [item.recommendation_id, item.explanation?.reason || ""]),
  );

  return (
    <Card
      title="Advisory recommendations"
      className="ic-panel"
      size="small"
      extra={<Text type="secondary">Advisory only — never auto-applied</Text>}
    >
      <List
        dataSource={recommendations}
        renderItem={(item) => (
          <List.Item>
            <List.Item.Meta
              title={
                <span>
                  <Text code>{item.recommendation_id}</Text>{" "}
                  <Tag>{item.priority || "—"}</Tag>
                  <Tag color="geekblue">{item.type || "—"}</Tag>
                  <Tag>{item.group || "—"}</Tag>
                </span>
              }
              description={
                <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  {reasonById.get(item.recommendation_id) ||
                    "Review related insights — no execution or deployment action."}
                </Paragraph>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
}

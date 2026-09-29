import { Button, Card, Empty, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { InsightSummaryRow } from "../types/console";

const { Text } = Typography;

type Props = {
  insights: InsightSummaryRow[];
  updatingId?: string | null;
  canUpdate?: boolean;
  onExplain: (insightId: string) => void;
  onAcknowledge: (insightId: string) => void;
  onResolve: (insightId: string) => void;
};

export function InsightCardList({
  insights,
  updatingId,
  canUpdate = false,
  onExplain,
  onAcknowledge,
  onResolve,
}: Props) {
  if (!insights.length) {
    return (
      <Card title="Findings" className="ic-panel" size="small">
        <Empty description="No insights" />
      </Card>
    );
  }

  const columns: ColumnsType<InsightSummaryRow> = [
    {
      title: "Insight",
      dataIndex: "insight_id",
      key: "insight_id",
      render: (v: string) => <Text code>{v}</Text>,
    },
    {
      title: "Severity",
      dataIndex: "severity",
      key: "severity",
      render: (v: string) => <Tag>{v || "—"}</Tag>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (v: string) => <Tag color="blue">{v || "—"}</Tag>,
    },
    {
      title: "Actions",
      key: "actions",
      render: (_, row) => (
        <Space wrap size="small">
          <Button size="small" onClick={() => onExplain(row.insight_id)}>
            Explain
          </Button>
          {canUpdate ? (
            <>
              <Button
                size="small"
                disabled={row.status === "ACKNOWLEDGED" || row.status === "RESOLVED"}
                loading={updatingId === row.insight_id}
                onClick={() => onAcknowledge(row.insight_id)}
              >
                Acknowledge
              </Button>
              <Button
                size="small"
                type="primary"
                disabled={row.status === "RESOLVED"}
                loading={updatingId === row.insight_id}
                onClick={() => onResolve(row.insight_id)}
              >
                Resolve
              </Button>
            </>
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <Card title="Findings" className="ic-panel" size="small">
      <Table
        rowKey="insight_id"
        size="small"
        pagination={false}
        columns={columns}
        dataSource={insights}
      />
    </Card>
  );
}

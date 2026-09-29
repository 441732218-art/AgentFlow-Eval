import { Table } from "antd";
import type { ColumnsType } from "antd/es/table";

type MetricRow = {
  key: string;
  metric: string;
  value: string;
};

type Props = {
  metrics: Record<string, number | null | undefined>;
  loading?: boolean;
};

export function MetricTable({ metrics, loading }: Props) {
  const rows: MetricRow[] = Object.entries(metrics)
    .filter(([, value]) => value != null)
    .map(([metric, value]) => ({
      key: metric,
      metric,
      value: String(value),
    }));

  const columns: ColumnsType<MetricRow> = [
    { title: "Metric", dataIndex: "metric", key: "metric" },
    { title: "Value", dataIndex: "value", key: "value" },
  ];

  return (
    <Table
      rowKey="key"
      size="small"
      loading={loading}
      columns={columns}
      dataSource={rows}
      pagination={false}
      locale={{ emptyText: "No metrics" }}
    />
  );
}

import { Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { AgentVersionRow } from "../types/agent";
import { LifecycleTag } from "./AgentStatus";

const { Text } = Typography;

export interface VersionTableProps {
  versions: AgentVersionRow[];
  loading?: boolean;
}

export function VersionTable({ versions, loading }: VersionTableProps) {
  const columns: ColumnsType<AgentVersionRow> = [
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: "Created Time",
      dataIndex: "created_at",
      key: "created_at",
      render: (value?: string | null) => (value ? new Date(value).toLocaleString() : "—"),
    },
    {
      title: "Immutable",
      dataIndex: "status",
      key: "immutable",
      render: (value: string) => <LifecycleTag status={value} />,
    },
    {
      title: "Evaluation Score",
      dataIndex: "evaluation_score",
      key: "evaluation_score",
      render: (value: number | null | undefined) => (value != null ? `${value}` : "—"),
    },
    {
      title: "Benchmark Result",
      dataIndex: "benchmark_result",
      key: "benchmark_result",
      render: (value?: string | null) => value ?? "—",
    },
    {
      title: "Deployment Status",
      dataIndex: "deployment_status",
      key: "deployment_status",
      render: (value?: string | null) => (value ? <Text code>{value}</Text> : "—"),
    },
  ];

  return (
    <Table
      rowKey={(row) => `${row.agent_id}-${row.version}`}
      columns={columns}
      dataSource={versions}
      loading={loading}
      pagination={false}
      size="middle"
    />
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, Card, Space, Table, Typography, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { runtimeApi, type ExecutionSummary } from "@/api/runtime";
import { ExecutionStatusTag, formatDurationMs } from "./ExecutionStatusTag";

const { Text } = Typography;

type Props = {
  agentId: string;
  limit?: number;
};

export function RecentExecutions({ agentId, limit = 20 }: Props) {
  const navigate = useNavigate();
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await runtimeApi.listExecutions({ agent_id: agentId, limit });
      setExecutions(data.items ?? []);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load recent executions");
    } finally {
      setLoading(false);
    }
  }, [agentId, limit]);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  const columns: ColumnsType<ExecutionSummary> = [
    {
      title: "Execution ID",
      dataIndex: "execution_id",
      key: "execution_id",
      render: (value: string) => (
        <Link to={`/executions/${value}`}>
          <Text code>{value.slice(0, 12)}…</Text>
        </Link>
      ),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (value: string) => <ExecutionStatusTag status={value} />,
    },
    {
      title: "Started",
      dataIndex: "started_at",
      key: "started_at",
      render: (value?: string) => (value ? new Date(value).toLocaleString() : "—"),
    },
    {
      title: "Duration",
      key: "duration",
      render: (_, row) => formatDurationMs(row.duration_ms, row.duration),
    },
    {
      title: "Trace",
      key: "trace",
      render: (_, row) =>
        row.trace_available ? (
          <Button
            type="link"
            size="small"
            onClick={() => navigate(`/agents/${agentId}/trace?executionId=${row.execution_id}`)}
          >
            View
          </Button>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
  ];

  return (
    <Card
      className="ic-panel"
      title={`Recent Executions (last ${limit})`}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} size="small" onClick={() => void loadExecutions()}>
            Refresh
          </Button>
          <Button type="link" size="small" onClick={() => navigate(`/agents/${agentId}/executions`)}>
            View all
          </Button>
        </Space>
      }
    >
      <Table
        rowKey="execution_id"
        size="small"
        loading={loading}
        columns={columns}
        dataSource={executions}
        pagination={false}
        locale={{ emptyText: "No executions recorded yet" }}
      />
    </Card>
  );
}

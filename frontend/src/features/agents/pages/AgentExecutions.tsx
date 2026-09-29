import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext } from "react-router-dom";
import { Button, Card, Space, Table, Typography, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { runtimeApi, type ExecutionSummary } from "@/api/runtime";
import { ExecutionStatusTag, formatDurationMs } from "../components/ExecutionStatusTag";
import type { AgentDetail } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
};

function summarizeResult(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return value.length > 80 ? `${value.slice(0, 80)}…` : value;
  try {
    const text = JSON.stringify(value);
    return text.length > 80 ? `${text.slice(0, 80)}…` : text;
  } catch {
    return String(value);
  }
}

export default function AgentExecutions() {
  const { agent } = useOutletContext<OutletContext>();
  const navigate = useNavigate();
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadExecutions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await runtimeApi.listExecutions({ agent_id: agent.id, limit: 100 });
      setExecutions(data.items ?? []);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load executions");
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  const columns: ColumnsType<ExecutionSummary> = [
    {
      title: "Execution ID",
      dataIndex: "execution_id",
      key: "execution_id",
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (value: string) => <ExecutionStatusTag status={value} />,
    },
    {
      title: "Duration",
      key: "duration",
      render: (_, row) => formatDurationMs(row.duration_ms, row.duration),
    },
    {
      title: "Result",
      key: "result",
      ellipsis: true,
      render: (_, row) => summarizeResult(row.result ?? row.error),
    },
    {
      title: "Trace",
      key: "trace",
      render: (_, row) => (
        <Space size="small">
          <Link to={`/executions/${row.execution_id}`}>Detail</Link>
          {row.trace_available ? (
            <Button
              type="link"
              size="small"
              onClick={() => navigate(`/agents/${agent.id}/trace?executionId=${row.execution_id}`)}
            >
              Trace
            </Button>
          ) : null}
        </Space>
      ),
    },
    {
      title: "Evidence",
      key: "evidence",
      render: (_, row) => (
        <Button
          type="link"
          size="small"
          onClick={() => navigate(`/agents/${agent.id}/trace?executionId=${row.execution_id}`)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <Card
      className="ic-panel"
      title="Executions"
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => void loadExecutions()} loading={loading}>
          Refresh
        </Button>
      }
    >
      <Paragraph type="secondary">
        Read-only execution history for <Text code>{agent.id}</Text>. Trace and evidence are
        available from the Trace tab or execution detail page.
      </Paragraph>
      <Table
        rowKey="execution_id"
        loading={loading}
        columns={columns}
        dataSource={executions}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        locale={{ emptyText: "No executions for this agent" }}
      />
    </Card>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Button, Card, Descriptions, Space, Typography, message } from "antd";
import { ArrowLeftOutlined, ApartmentOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { runtimeApi, type ExecutionSummary } from "@/api/runtime";
import { ExecutionStatusTag, formatDurationMs } from "@/features/agents/components/ExecutionStatusTag";

const { Paragraph, Text } = Typography;

function formatResult(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function ExecutionDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [execution, setExecution] = useState<ExecutionSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadExecution = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await runtimeApi.getExecution(id);
      setExecution(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load execution");
      setExecution(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadExecution();
  }, [loadExecution]);

  if (loading && !execution) {
    return <PageSkeleton variant="detail" />;
  }

  if (!execution) {
    return (
      <PageShell title="Execution not found">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          Back
        </Button>
      </PageShell>
    );
  }

  const agentId = execution.agent_id;

  return (
    <PageShell
      title="Execution Detail"
      subtitle={execution.execution_id}
      icon={<ApartmentOutlined />}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadExecution()}>
            Refresh
          </Button>
          {agentId ? (
            <Button onClick={() => navigate(`/agents/${agentId}`)}>Agent overview</Button>
          ) : null}
        </Space>
      }
    >
      <Card className="ic-panel">
        <Descriptions bordered column={1} size="small">
          <Descriptions.Item label="Execution ID">
            <Text code>{execution.execution_id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="Agent">
            {agentId ? <Link to={`/agents/${agentId}`}>{agentId}</Link> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            <ExecutionStatusTag status={execution.status} />
          </Descriptions.Item>
          <Descriptions.Item label="Duration">
            {formatDurationMs(execution.duration_ms, execution.duration)}
          </Descriptions.Item>
          <Descriptions.Item label="Started">
            {execution.started_at || execution.created_at
              ? new Date(execution.started_at ?? execution.created_at!).toLocaleString()
              : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Completed">
            {execution.completed_at || execution.updated_at
              ? new Date(execution.completed_at ?? execution.updated_at!).toLocaleString()
              : "—"}
          </Descriptions.Item>
        </Descriptions>

        {agentId && execution.trace_available !== false ? (
          <Paragraph style={{ marginTop: 16 }}>
            <Link to={`/agents/${agentId}/trace?executionId=${execution.execution_id}`}>
              Open runtime trace
            </Link>
          </Paragraph>
        ) : null}

        <Paragraph style={{ marginTop: 16 }}>
          <Text strong>Result</Text>
        </Paragraph>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: 12 }}>
          {formatResult(execution.result ?? execution.error)}
        </pre>
      </Card>
    </PageShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, Space, Table, Tag, Typography, message } from "antd";
import { AuditOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { DecisionBadge } from "@/components/governance/DecisionBadge";
import { governanceApi, type QualityGateRow } from "@/api/governance";

const { Text } = Typography;

export default function QualityGateDashboard() {
  const [rows, setRows] = useState<QualityGateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await governanceApi.listQualityGates();
      setRows(data.items);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load quality gates";
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const columns: ColumnsType<QualityGateRow> = [
    {
      title: "Agent",
      key: "agent",
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text strong>{row.agent_name}</Text>
          <Text type="secondary" code>
            {row.agent_id}
          </Text>
        </Space>
      ),
    },
    {
      title: "Current Version",
      dataIndex: "current_version",
      key: "current_version",
      render: (value: string | null) => (value ? <Tag>{value}</Tag> : "—"),
    },
    {
      title: "Latest Evaluation",
      key: "evaluation",
      render: (_, row) =>
        row.latest_evaluation_id ? (
          <Link to={`/governance/evaluations/${row.latest_evaluation_id}`}>
            {row.evaluation_score != null ? `${row.evaluation_score}%` : row.evaluation_status ?? "View"}
          </Link>
        ) : (
          "—"
        ),
    },
    {
      title: "Benchmark",
      key: "benchmark",
      render: (_, row) =>
        row.benchmark_id ? (
          <Link to={`/governance/benchmarks/${row.benchmark_id}`}>
            {row.benchmark_delta != null
              ? `${row.benchmark_delta >= 0 ? "+" : ""}${row.benchmark_delta}%`
              : row.benchmark_status ?? "View"}
          </Link>
        ) : (
          "—"
        ),
    },
    {
      title: "Quality Gate",
      key: "quality_gate",
      render: (_, row) =>
        row.release_assessment_id ? (
          <Link to={`/governance/releases/${row.release_assessment_id}`}>
            <DecisionBadge decision={row.quality_gate} />
          </Link>
        ) : (
          <DecisionBadge decision={row.quality_gate} />
        ),
    },
    {
      title: "Deployment",
      dataIndex: "deployment_status",
      key: "deployment_status",
      render: (value: string) => <Tag>{value}</Tag>,
    },
  ];

  if (loading && rows.length === 0 && !error) {
    return <PageSkeleton variant="cards" />;
  }

  return (
    <PageShell
      title="Quality Gate Dashboard"
      subtitle="Agent quality overview across evaluation, benchmark, and release governance"
      icon={<AuditOutlined />}
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
          Refresh
        </Button>
      }
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          message="Unable to load quality gates"
          description={error}
          action={
            <Button size="small" onClick={() => void loadData()}>
              Retry
            </Button>
          }
          style={{ marginBottom: 16 }}
        />
      ) : null}
      {!loading && rows.length === 0 && !error ? (
        <EmptyState
          title="No agents yet"
          description="Create and evaluate agents to populate the governance console."
        />
      ) : (
        <Table
          rowKey="agent_id"
          loading={loading}
          columns={columns}
          dataSource={rows}
          pagination={{ pageSize: 10 }}
        />
      )}
    </PageShell>
  );
}

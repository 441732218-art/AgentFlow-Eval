import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Alert, Button, Space, Table, Tag, Typography, message } from "antd";
import { ArrowLeftOutlined, ReloadOutlined, SafetyCertificateOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { governanceApi, type DeploymentPolicyRow } from "@/api/governance";

const { Text } = Typography;

export default function DeploymentPoliciesPage() {
  const [policies, setPolicies] = useState<DeploymentPolicyRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await governanceApi.listDeploymentPolicies();
      setPolicies(data.policies);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load deployment policies";
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const columns: ColumnsType<DeploymentPolicyRow> = [
    {
      title: "Agent",
      key: "agent",
      render: (_, row) => (
        <Space direction="vertical" size={0}>
          <Text strong>{row.agent_name ?? row.agent_id}</Text>
          <Text type="secondary" code>
            {row.agent_id}
          </Text>
        </Space>
      ),
    },
    {
      title: "Minimum Score",
      dataIndex: "min_score",
      key: "min_score",
      render: (value: number | null) => (value != null ? value : "—"),
    },
    {
      title: "Required Metrics",
      key: "required_metrics",
      render: (_, row) =>
        Object.keys(row.required_metrics).length
          ? Object.entries(row.required_metrics)
              .map(([key, val]) => `${key}: ${val}`)
              .join(", ")
          : "—",
    },
    {
      title: "Evaluation Required",
      dataIndex: "evaluation_required",
      key: "evaluation_required",
      render: (value: boolean) => (value ? "Yes" : "No"),
    },
    {
      title: "Gate Enabled",
      dataIndex: "gate_enabled",
      key: "gate_enabled",
      render: (value: boolean) =>
        value ? <Tag color="success">Enabled</Tag> : <Tag>Disabled</Tag>,
    },
  ];

  if (loading && policies.length === 0 && !error) {
    return <PageSkeleton variant="cards" />;
  }

  return (
    <PageShell
      title="Deployment Policies"
      subtitle="View-only quality gate policies per agent"
      icon={<SafetyCertificateOutlined />}
      extra={
        <Space>
          <Link to="/governance/quality-gates">
            <Button icon={<ArrowLeftOutlined />}>Back</Button>
          </Link>
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
            Refresh
          </Button>
        </Space>
      }
    >
      {error ? (
        <Alert
          type="error"
          showIcon
          message="Unable to load policies"
          description={error}
          style={{ marginBottom: 16 }}
        />
      ) : null}
      {!loading && policies.length === 0 && !error ? (
        <EmptyState title="No policies" description="No deployment policies configured yet." />
      ) : (
        <Table
          rowKey="agent_id"
          loading={loading}
          columns={columns}
          dataSource={policies}
          pagination={{ pageSize: 10 }}
        />
      )}
    </PageShell>
  );
}

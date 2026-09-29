import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Alert, Button, Card, Space, Table, Typography, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { agentsApi } from "../api/agents";
import { DeploymentStatus } from "../components/DeploymentStatus";
import type { AgentDeployment, AgentDetail } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
};

type DeploymentRow = AgentDeployment & {
  updated_at?: string | null;
};

export default function AgentDeployments() {
  const { agent } = useOutletContext<OutletContext>();
  const [deployments, setDeployments] = useState<DeploymentRow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const deploymentData = await agentsApi.listDeployments(agent.id);
      setDeployments(deploymentData.deployments);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load deployments");
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const deploymentColumns: ColumnsType<DeploymentRow> = [
    {
      title: "Environment",
      dataIndex: "environment",
      key: "environment",
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: "Active Version",
      dataIndex: "version",
      key: "version",
      render: (value: string, row) =>
        row.status === "ACTIVE" ? <Text code>{value}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "Deployment Status",
      key: "status",
      render: (_, row) => <DeploymentStatus deployment={row} />,
    },
    {
      title: "Updated Time",
      dataIndex: "updated_at",
      key: "updated_at",
      render: (value?: string | null) =>
        value ? new Date(value).toLocaleString() : <Text type="secondary">—</Text>,
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card
        className="ic-panel"
        title="Deployments"
        extra={
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
            Refresh
          </Button>
        }
      >
        <Alert
          type="info"
          showIcon
          message="Read-only deployment view"
          description="Deployment actions follow governance decisions. Deploy and rollback controls are not exposed in this console phase."
          style={{ marginBottom: 16 }}
        />
        <Paragraph type="secondary">
          Active deployments per environment for agent <Text code>{agent.id}</Text>.
        </Paragraph>
        <Table
          rowKey={(row) => `${row.environment}-${row.version}-${row.status}`}
          loading={loading}
          columns={deploymentColumns}
          dataSource={deployments}
          pagination={false}
          locale={{ emptyText: "No deployments recorded" }}
        />
      </Card>
    </Space>
  );
}

import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import {
  Button,
  Card,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { ExperimentOutlined, PlayCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import { agentsApi } from "../api/agents";
import type { AgentDetail, AgentVersion, EvaluationSummary } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
  reloadAgent: () => void;
};

function statusColor(status: string): string {
  switch (status) {
    case "completed":
      return "success";
    case "partial":
      return "warning";
    case "failed":
      return "error";
    case "running":
      return "processing";
    default:
      return "default";
  }
}

export default function AgentEvaluations() {
  const { id = "" } = useParams<{ id: string }>();
  const { agent } = useOutletContext<OutletContext>();
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [runOpen, setRunOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<string>("");
  const [running, setRunning] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [evalData, versionData] = await Promise.all([
        agentsApi.listEvaluations(id || agent.id),
        agentsApi.listVersions(id || agent.id),
      ]);
      setEvaluations(evalData.evaluations);
      setVersions(versionData.versions);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load evaluations");
    } finally {
      setLoading(false);
    }
  }, [id, agent.id]);

  useEffect(() => {
    if (!selectedVersion && versions.length > 0) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleRunEvaluation = async () => {
    const version = selectedVersion.trim();
    if (!version) {
      message.warning("Select a published version");
      return;
    }
    setRunning(true);
    try {
      await agentsApi.startEvaluation(agent.id, { agent_version: version });
      message.success(`Evaluation started for version ${version}`);
      setRunOpen(false);
      await loadData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setRunning(false);
    }
  };

  const columns = [
    {
      title: "Version",
      dataIndex: "agent_version",
      key: "agent_version",
      render: (value: string) => <Tag>{value}</Tag>,
    },
    {
      title: "Score",
      dataIndex: "score",
      key: "score",
      render: (value: number | null | undefined) =>
        value != null ? `${value}` : "—",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>,
    },
    {
      title: "Created",
      dataIndex: "started_at",
      key: "started_at",
      render: (value: string) => new Date(value).toLocaleString(),
    },
  ];

  return (
    <Card
      className="ic-panel"
      title={
        <Space>
          <ExperimentOutlined />
          Evaluation Runs
        </Space>
      }
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => setRunOpen(true)}
            disabled={versions.length === 0}
          >
            Run Evaluation
          </Button>
        </Space>
      }
    >
      <Paragraph type="secondary">
        Evaluate published agent versions before deployment. Scores use the existing V1 LLM Judge
        and metric pipeline.
      </Paragraph>
      {versions.length === 0 ? (
        <Text type="warning">Publish a version first to run evaluations.</Text>
      ) : null}
      <Table
        rowKey="evaluation_id"
        loading={loading}
        dataSource={evaluations}
        columns={columns}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: "No evaluations yet" }}
      />

      <Modal
        title="Run Version Evaluation"
        open={runOpen}
        onCancel={() => setRunOpen(false)}
        onOk={() => void handleRunEvaluation()}
        confirmLoading={running}
        okText="Run"
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <Text>Select a published version to evaluate:</Text>
          <Select
            style={{ width: "100%" }}
            value={selectedVersion || undefined}
            onChange={setSelectedVersion}
            options={versions.map((v) => ({ label: v.version, value: v.version }))}
          />
        </Space>
      </Modal>
    </Card>
  );
}

import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Alert,
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
import {
  AuditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { agentsApi } from "../api/agents";
import type { AgentDetail, AgentVersion, ReleaseAssessment } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
  reloadAgent: () => void;
};

function decisionTag(decision: string) {
  switch (decision) {
    case "APPROVE":
      return (
        <Tag icon={<CheckCircleOutlined />} color="success">
          APPROVE
        </Tag>
      );
    case "REJECT":
      return (
        <Tag icon={<CloseCircleOutlined />} color="error">
          REJECT
        </Tag>
      );
    case "WARNING":
      return (
        <Tag icon={<ExclamationCircleOutlined />} color="warning">
          WARNING
        </Tag>
      );
    default:
      return <Tag>{decision}</Tag>;
  }
}

export default function AgentReleaseReadiness() {
  const { agent } = useOutletContext<OutletContext>();
  const [assessments, setAssessments] = useState<ReleaseAssessment[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [assessOpen, setAssessOpen] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState("");
  const [assessing, setAssessing] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [assessmentData, versionData] = await Promise.all([
        agentsApi.listReleaseAssessments(agent.id),
        agentsApi.listVersions(agent.id),
      ]);
      setAssessments(assessmentData.assessments);
      setVersions(versionData.versions);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load release assessments");
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (!selectedVersion && versions.length > 0) {
      setSelectedVersion(versions[0].version);
    }
  }, [versions, selectedVersion]);

  const handleAssess = async () => {
    const version = selectedVersion.trim();
    if (!version) {
      message.warning("Select a version to assess");
      return;
    }
    setAssessing(true);
    try {
      const result = await agentsApi.createReleaseAssessment(agent.id, { version });
      message.success(`Release decision: ${result.decision}`);
      setAssessOpen(false);
      await loadData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Assessment failed");
    } finally {
      setAssessing(false);
    }
  };

  const columns: ColumnsType<ReleaseAssessment> = [
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: "Score",
      dataIndex: "score",
      key: "score",
      render: (value: number | null) => (value != null ? `${value}` : "—"),
    },
    {
      title: "Delta",
      dataIndex: "score_delta",
      key: "score_delta",
      render: (value: number | null) =>
        value != null ? (
          <Text type={value >= 0 ? "success" : "danger"}>
            {value >= 0 ? "+" : ""}
            {value}
          </Text>
        ) : (
          "—"
        ),
    },
    {
      title: "Regression",
      dataIndex: "regression_detected",
      key: "regression_detected",
      render: (value: boolean | null) =>
        value == null ? "—" : value ? <Tag color="error">true</Tag> : <Tag color="success">false</Tag>,
    },
    {
      title: "Decision",
      dataIndex: "decision",
      key: "decision",
      render: (value: string) => decisionTag(value),
    },
    {
      title: "Reasons",
      dataIndex: "reasons",
      key: "reasons",
      render: (reasons: string[]) => (
        <Typography.Paragraph style={{ margin: 0 }} ellipsis={{ rows: 2, expandable: true }}>
          {reasons.join("; ")}
        </Typography.Paragraph>
      ),
    },
  ];

  const latest = assessments[0];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      {latest ? (
        <Alert
          type={
            latest.decision === "APPROVE"
              ? "success"
              : latest.decision === "WARNING"
                ? "warning"
                : "error"
          }
          showIcon
          message={`Latest decision for v${latest.version}: ${latest.decision}`}
          description={latest.reasons.join("; ")}
        />
      ) : null}

      <Card
        className="ic-panel"
        title={
          <Space>
            <AuditOutlined />
            Release Readiness
          </Space>
        }
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
              Refresh
            </Button>
            <Button
              type="primary"
              onClick={() => setAssessOpen(true)}
              disabled={versions.length === 0}
            >
              Assess Release
            </Button>
          </Space>
        }
      >
        <Paragraph type="secondary">
          Combines evaluation score, benchmark regression, and deployment policy to explain why a
          version can or cannot go to production.
        </Paragraph>
        <Table
          rowKey="assessment_id"
          loading={loading}
          columns={columns}
          dataSource={assessments}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: "No release assessments yet" }}
        />
      </Card>

      <Modal
        title="Assess Version Release Readiness"
        open={assessOpen}
        onCancel={() => setAssessOpen(false)}
        onOk={() => void handleAssess()}
        confirmLoading={assessing}
        okText="Assess"
      >
        <Select
          style={{ width: "100%" }}
          value={selectedVersion || undefined}
          onChange={setSelectedVersion}
          options={versions.map((v) => ({ label: v.version, value: v.version }))}
        />
      </Modal>
    </Space>
  );
}

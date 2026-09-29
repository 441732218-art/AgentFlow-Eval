import { useCallback, useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import {
  Button,
  Card,
  Descriptions,
  Space,
  Table,
  Typography,
  message,
} from "antd";
import { AuditOutlined, ReloadOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { governanceApi, type QualityGateRow } from "@/api/governance";
import { DecisionBadge } from "@/components/governance/DecisionBadge";
import { agentsApi } from "../api/agents";
import type { AgentDetail, DeploymentPolicy, ReleaseAssessment } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
};

export default function AgentGovernance() {
  const { agent } = useOutletContext<OutletContext>();
  const [gateRow, setGateRow] = useState<QualityGateRow | null>(null);
  const [policy, setPolicy] = useState<DeploymentPolicy | null>(null);
  const [assessments, setAssessments] = useState<ReleaseAssessment[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [gates, policyData, releaseData] = await Promise.all([
        governanceApi.listQualityGates(),
        agentsApi.getDeploymentPolicy(agent.id).catch(() => null),
        agentsApi.listReleaseAssessments(agent.id).catch(() => ({ assessments: [], count: 0 })),
      ]);
      setGateRow(gates.items.find((item) => item.agent_id === agent.id) ?? null);
      setPolicy(policyData ?? null);
      setAssessments(releaseData.assessments);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load governance data");
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const assessmentColumns: ColumnsType<ReleaseAssessment> = [
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
      render: (value: string) => <Text code>{value}</Text>,
    },
    {
      title: "Decision",
      dataIndex: "decision",
      key: "decision",
      render: (value: string) => <DecisionBadge decision={value} />,
    },
    {
      title: "Score",
      dataIndex: "score",
      key: "score",
      render: (value: number | null) => (value != null ? `${value}` : "—"),
    },
    {
      title: "Assessed",
      dataIndex: "assessed_at",
      key: "assessed_at",
      render: (value: string) => (value ? new Date(value).toLocaleString() : "—"),
    },
    {
      title: "Detail",
      key: "detail",
      render: (_, row) => (
        <Link to={`/governance/releases/${row.assessment_id}`}>Release assessment</Link>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card
        className="ic-panel"
        title="Governance Overview"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
              Refresh
            </Button>
            <Link to="/governance/quality-gates">
              <Button icon={<AuditOutlined />}>Quality Gate Console</Button>
            </Link>
          </Space>
        }
      >
        <Paragraph type="secondary">
          Governance decisions gate deployment actions. This view is read-only — publish, deploy,
          and release actions follow the governance workflow.
        </Paragraph>
        <Descriptions bordered size="small" column={1}>
          <Descriptions.Item label="Quality Gate">
            <DecisionBadge decision={gateRow?.quality_gate} />
          </Descriptions.Item>
          <Descriptions.Item label="Current Version">
            {gateRow?.current_version ? <Text code>{gateRow.current_version}</Text> : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Deployment Status">
            {gateRow?.deployment_status ?? "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Latest Evaluation">
            {gateRow?.latest_evaluation_id ? (
              <Link to={`/governance/evaluations/${gateRow.latest_evaluation_id}`}>
                {gateRow.latest_evaluation_id}
                {gateRow.evaluation_score != null ? ` (${gateRow.evaluation_score})` : ""}
              </Link>
            ) : (
              "—"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Latest Benchmark">
            {gateRow?.benchmark_id ? (
              <Link to={`/governance/benchmarks/${gateRow.benchmark_id}`}>
                {gateRow.benchmark_id}
              </Link>
            ) : (
              "—"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Deployment Policy">
            {policy ? (
              <>
                Gate {policy.gate_enabled ? "enabled" : "disabled"}
                {policy.min_score != null ? ` · min score ${policy.min_score}` : ""}
              </>
            ) : (
              "—"
            )}
          </Descriptions.Item>
        </Descriptions>
        <Paragraph style={{ marginTop: 16 }}>
          <Link to="/governance/policies">View all deployment policies</Link>
        </Paragraph>
      </Card>

      <Card className="ic-panel" title="Release Assessments">
        <Table
          rowKey="assessment_id"
          loading={loading}
          columns={assessmentColumns}
          dataSource={assessments}
          pagination={false}
          locale={{ emptyText: "No release assessments yet" }}
        />
      </Card>
    </Space>
  );
}

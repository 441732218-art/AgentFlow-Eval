import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Space, Table, Typography, message } from "antd";
import { ArrowLeftOutlined, ExperimentOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { GovernanceScoreCard } from "@/components/governance/GovernanceScoreCard";
import { MetricTable } from "@/components/governance/MetricTable";
import { governanceApi, type GovernanceEvaluationDetail } from "@/api/governance";
import { formatDateTime } from "@/utils/format";

const { Text } = Typography;

export default function EvaluationDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GovernanceEvaluationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setDetail(await governanceApi.getEvaluation(id));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load evaluation";
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  if (loading && !detail && !error) {
    return <PageSkeleton variant="detail" />;
  }

  return (
    <PageShell
      title="Evaluation Detail"
      subtitle={id}
      icon={<ExperimentOutlined />}
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
        <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />
      ) : null}
      {detail ? (
        <Space direction="vertical" size="large" style={{ width: "100%" }}>
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="Evaluation ID">
              <Text code>{detail.evaluation_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Agent">{detail.agent_id}</Descriptions.Item>
            <Descriptions.Item label="Version">{detail.agent_version}</Descriptions.Item>
            <Descriptions.Item label="Status">{detail.status}</Descriptions.Item>
            <Descriptions.Item label="Judge Mode">{detail.judge_mode ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="Token Cost">{detail.token_cost}</Descriptions.Item>
            <Descriptions.Item label="Completed">
              {detail.completed_at ? formatDateTime(detail.completed_at) : "—"}
            </Descriptions.Item>
          </Descriptions>

          <GovernanceScoreCard label="Score" score={detail.score} />

          <Card className="ic-panel" title="Metrics">
            <MetricTable metrics={detail.metrics} />
          </Card>

          <Card className="ic-panel" title="Failures">
            <Table
              rowKey="case_name"
              size="small"
              pagination={false}
              dataSource={detail.failures}
              locale={{ emptyText: "No failures" }}
              columns={[
                { title: "Case", dataIndex: "case_name", key: "case_name" },
                { title: "Status", dataIndex: "status", key: "status" },
                { title: "Score", dataIndex: "score", key: "score" },
                { title: "Reason", dataIndex: "reason", key: "reason" },
              ]}
            />
          </Card>
        </Space>
      ) : null}
    </PageShell>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Button, Card, Descriptions, Space, Typography, message } from "antd";
import { ArrowLeftOutlined, AuditOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { DecisionBadge } from "@/components/governance/DecisionBadge";
import { MetricTable } from "@/components/governance/MetricTable";
import { governanceApi, type GovernanceReleaseDetail } from "@/api/governance";
import { formatDateTime } from "@/utils/format";

const { Text, Paragraph } = Typography;

export default function ReleaseAssessmentDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GovernanceReleaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setDetail(await governanceApi.getReleaseAssessment(id));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load release assessment";
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
      title="Release Decision"
      subtitle={id}
      icon={<AuditOutlined />}
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
            <Descriptions.Item label="Assessment ID">
              <Text code>{detail.assessment_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Agent">{detail.agent_id}</Descriptions.Item>
            <Descriptions.Item label="Version">{detail.version}</Descriptions.Item>
            <Descriptions.Item label="Decision">
              <DecisionBadge decision={detail.decision} />
            </Descriptions.Item>
            <Descriptions.Item label="Score">{detail.score ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="Score Delta">{detail.score_delta ?? "—"}</Descriptions.Item>
            <Descriptions.Item label="Evaluation">
              {detail.evaluation_id ? (
                <Link to={`/governance/evaluations/${detail.evaluation_id}`}>
                  {detail.evaluation_id}
                </Link>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Benchmark">
              {detail.benchmark_id ? (
                <Link to={`/governance/benchmarks/${detail.benchmark_id}`}>
                  {detail.benchmark_id}
                </Link>
              ) : (
                "—"
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Assessed At">
              {formatDateTime(detail.assessed_at)}
            </Descriptions.Item>
          </Descriptions>

          <Card className="ic-panel" title="Reasons">
            <Paragraph style={{ marginBottom: 0 }}>
              {detail.reasons.length ? detail.reasons.join("; ") : "No reasons recorded"}
            </Paragraph>
          </Card>

          {detail.policy ? (
            <Card className="ic-panel" title="Deployment Policy">
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="Minimum Score">
                  {detail.policy.min_score ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Evaluation Required">
                  {detail.policy.evaluation_required ? "Yes" : "No"}
                </Descriptions.Item>
                <Descriptions.Item label="Gate Enabled">
                  {detail.policy.gate_enabled ? "Yes" : "No"}
                </Descriptions.Item>
              </Descriptions>
              <MetricTable metrics={detail.policy.required_metrics} />
            </Card>
          ) : null}
        </Space>
      ) : null}
    </PageShell>
  );
}

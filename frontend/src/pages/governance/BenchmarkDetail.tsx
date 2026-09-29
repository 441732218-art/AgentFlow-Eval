import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Alert, Button, Descriptions, Space, Tag, Typography, message } from "antd";
import { ArrowLeftOutlined, LineChartOutlined, ReloadOutlined } from "@ant-design/icons";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { BenchmarkDiff } from "@/components/governance/BenchmarkDiff";
import { DecisionBadge } from "@/components/governance/DecisionBadge";
import { governanceApi, type GovernanceBenchmarkDetail } from "@/api/governance";
import { formatDateTime } from "@/utils/format";

const { Text } = Typography;

export default function BenchmarkDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GovernanceBenchmarkDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      setDetail(await governanceApi.getBenchmark(id));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load benchmark";
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
      title="Benchmark Comparison"
      subtitle={id}
      icon={<LineChartOutlined />}
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
            <Descriptions.Item label="Benchmark ID">
              <Text code>{detail.benchmark_id}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="Agent">{detail.agent_id}</Descriptions.Item>
            <Descriptions.Item label="Status">{detail.status}</Descriptions.Item>
            <Descriptions.Item label="Regression">
              {detail.regression_detected == null ? (
                "—"
              ) : detail.regression_detected ? (
                <Tag color="error">Detected</Tag>
              ) : (
                <Tag color="success">None</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="Decision">
              <DecisionBadge decision={detail.decision} />
            </Descriptions.Item>
            <Descriptions.Item label="Completed">
              {detail.completed_at ? formatDateTime(detail.completed_at) : "—"}
            </Descriptions.Item>
          </Descriptions>

          <BenchmarkDiff
            baselineVersion={detail.baseline_version}
            candidateVersion={detail.candidate_version}
            baselineScore={detail.baseline_score}
            candidateScore={detail.candidate_score}
            scoreDelta={detail.score_delta}
            metricComparison={detail.metric_comparison}
          />
        </Space>
      ) : null}
    </PageShell>
  );
}

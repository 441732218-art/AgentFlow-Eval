import { Card, Col, Row, Space, Typography } from "antd";
import { ArrowRightOutlined } from "@ant-design/icons";
import { MetricTable } from "./MetricTable";

const { Text } = Typography;

type Props = {
  baselineVersion: string;
  candidateVersion: string;
  baselineScore: number | null;
  candidateScore: number | null;
  scoreDelta: number | null;
  metricComparison: Record<string, number | null | undefined>;
};

export function BenchmarkDiff({
  baselineVersion,
  candidateVersion,
  baselineScore,
  candidateScore,
  scoreDelta,
  metricComparison,
}: Props) {
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card className="ic-panel" size="small" title="Version Comparison">
        <Space wrap>
          <Text code>{baselineVersion}</Text>
          <ArrowRightOutlined />
          <Text code>{candidateVersion}</Text>
        </Space>
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col xs={24} md={8}>
            <Text type="secondary">Baseline</Text>
            <div>
              <Text strong>{baselineScore ?? "—"}</Text>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <Text type="secondary">Candidate</Text>
            <div>
              <Text strong>{candidateScore ?? "—"}</Text>
            </div>
          </Col>
          <Col xs={24} md={8}>
            <Text type="secondary">Delta</Text>
            <div>
              <Text strong type={scoreDelta != null && scoreDelta >= 0 ? "success" : "danger"}>
                {scoreDelta != null ? `${scoreDelta >= 0 ? "+" : ""}${scoreDelta}` : "—"}
              </Text>
            </div>
          </Col>
        </Row>
      </Card>
      <Card className="ic-panel" size="small" title="Metric Comparison">
        <MetricTable metrics={metricComparison} />
      </Card>
    </Space>
  );
}

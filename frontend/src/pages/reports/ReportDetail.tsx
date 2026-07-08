import { useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Statistic,
  Typography,
  Descriptions,
  Empty,
} from "antd";
import {
  DownloadOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useTaskReport } from "@/hooks";
import type { TaskReport } from "@/types";

const { Text, Title } = Typography;

const DIMENSION_LABELS: Record<string, string> = {
  tool_accuracy: "Tool Accuracy",
  answer_correctness: "Answer Correctness",
  reasoning_coherence: "Reasoning Coherence",
};

const DIMENSION_MAX: Record<string, number> = {
  tool_accuracy: 40,
  answer_correctness: 40,
  reasoning_coherence: 20,
};

function exportJson(data: TaskReport, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCsv(report: TaskReport) {
  const rows: string[] = ['"suite","status","tool_accuracy","answer_correctness","reasoning_coherence","total","tokens","time_ms"'];
  for (const d of report.details || []) {
    for (const t of d.traces || []) {
      const scores = t.scores || {};
      const total = Object.values(scores).reduce((a: number, b: number) => a + b, 0);
      rows.push(
        [
          `"${d.user_query.replace(/"/g, '""')}"`,
          t.status,
          scores.tool_accuracy ?? "",
          scores.answer_correctness ?? "",
          scores.reasoning_coherence ?? "",
          total,
          t.total_tokens,
          t.response_time_ms,
        ].join(",")
      );
    }
  }
  const blob = new Blob([rows.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "evaluation-report.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: report, isLoading, error, refetch } = useTaskReport(id);

  // Chart data
  const chartData = useMemo(() => {
    if (!report?.summary?.dimension_scores) return [];
    const ds = report.summary.dimension_scores;
    return Object.entries(DIMENSION_LABELS).map(([key, label]) => ({
      dimension: label,
      value: Math.round(((ds[key] || 0) / (DIMENSION_MAX[key] || 1)) * 100),
      raw: ds[key] || 0,
      max: DIMENSION_MAX[key] || 0,
    }));
  }, [report]);

  const handleExportJson = useCallback(() => {
    if (report) exportJson(report, `report-${id}.json`);
  }, [report, id]);

  const handleExportCsv = useCallback(() => {
    if (report) exportCsv(report);
  }, [report]);

  // Table columns
  const columns = [
    {
      title: "Suite",
      dataIndex: "user_query",
      key: "user_query",
      ellipsis: true,
      width: 250,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (s: string) => (
        <Tag color={s === "success" ? "success" : "error"}>{s}</Tag>
      ),
    },
    {
      title: "Tool Acc.",
      dataIndex: "tool_accuracy",
      key: "tool_accuracy",
      width: 100,
      render: (v: number) => v ?? "-",
    },
    {
      title: "Answer Corr.",
      dataIndex: "answer_correctness",
      key: "answer_correctness",
      width: 100,
      render: (v: number) => v ?? "-",
    },
    {
      title: "Reasoning Coh.",
      dataIndex: "reasoning_coherence",
      key: "reasoning_coherence",
      width: 100,
      render: (v: number) => v ?? "-",
    },
    {
      title: "Total",
      dataIndex: "total",
      key: "total",
      width: 80,
      render: (v: number) => <Text strong>{v}</Text>,
    },
    {
      title: "Tokens",
      dataIndex: "total_tokens",
      key: "total_tokens",
      width: 80,
    },
    {
      title: "Actions",
      key: "actions",
      width: 100,
      render: (_: unknown, record: { trace_id?: string }) =>
        record.trace_id ? (
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => id && navigate(`/tasks/${id}`)}
          >
            View Trace
          </Button>
        ) : null,
    },
  ];

  // Table data
  const tableData = useMemo(() => {
    const result: Array<Record<string, unknown>> = [];
    for (const d of report?.details || []) {
      for (const t of d.traces || []) {
        const scores = t.scores || {};
        result.push({
          key: t.trace_id,
          user_query: d.user_query,
          status: t.status,
          tool_accuracy: scores.tool_accuracy,
          answer_correctness: scores.answer_correctness,
          reasoning_coherence: scores.reasoning_coherence,
          total: Object.values(scores).reduce((a: number, b: number) => a + b, 0),
          total_tokens: t.total_tokens,
          trace_id: t.trace_id,
        });
      }
    }
    return result;
  }, [report]);

  // Loading
  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" tip="Loading report..." />
      </div>
    );
  }

  // Error
  if (error) {
    return (
      <Alert
        type="error"
        message="Failed to load report"
        description={(error as Error)?.message || "An error occurred"}
        showIcon
        action={<Button onClick={() => refetch()}>Retry</Button>}
      />
    );
  }

  // No data
  if (!report) {
    return (
      <Empty
        description="No report data available."
        style={{ padding: 80 }}
      >
        <Button onClick={() => id && navigate(`/tasks/${id}`)}>
          Back to Task
        </Button>
      </Empty>
    );
  }

  const summary = report.summary;

  return (
    <div>
      {/* ---- Header ---- */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="middle">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate(`/tasks/${id}`)}
              />
              <div>
                <Title level={4} style={{ margin: 0 }}>
                  Evaluation Report
                </Title>
                <Text type="secondary">
                  Task: {report.task?.name || id}
                </Text>
              </div>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<FileTextOutlined />} onClick={handleExportJson}>
                Export JSON
              </Button>
              <Button icon={<DownloadOutlined />} onClick={handleExportCsv}>
                Export CSV
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* ---- Stats ---- */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Overall Score"
              value={summary?.overall_score ?? 0}
              suffix="/ 100"
              valueStyle={{
                color: (summary?.overall_score ?? 0) >= 70 ? "#52c41a" : "#faad14",
                fontSize: 28,
              }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Total Suites" value={summary?.total_suites ?? 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Pass Rate"
              value={
                summary?.total_traces
                  ? Math.round((summary.success_count / summary.total_traces) * 100)
                  : 0
              }
              suffix="%"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Total Tokens"
              value={summary?.total_tokens ?? 0}
            />
          </Card>
        </Col>
      </Row>

      {/* ---- Radar Chart + Dimension Scores ---- */}
      {chartData.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Card title="Score Radar">
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={chartData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="dimension" />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar
                    dataKey="value"
                    stroke="#1677ff"
                    fill="#1677ff"
                    fillOpacity={0.3}
                  />
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col span={12}>
            <Card title="Dimension Scores">
              {chartData.map((d) => (
                <div key={d.dimension} style={{ marginBottom: 16 }}>
                  <Row justify="space-between">
                    <Col>
                      <Text>{d.dimension}</Text>
                    </Col>
                    <Col>
                      <Text strong>
                        {d.raw} / {d.max}
                      </Text>
                    </Col>
                  </Row>
                  <div
                    style={{
                      height: 8,
                      background: "#f0f0f0",
                      borderRadius: 4,
                      marginTop: 4,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${d.value}%`,
                        height: "100%",
                        background:
                          d.value >= 80
                            ? "#52c41a"
                            : d.value >= 50
                            ? "#1677ff"
                            : "#ff4d4f",
                        borderRadius: 4,
                        transition: "width 0.5s",
                      }}
                    />
                  </div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {d.value}% of max score
                  </Text>
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )}

      {/* ---- Detailed Scoring Table ---- */}
      <Card title="Detailed Scoring">
        {tableData.length > 0 ? (
          <Table
            dataSource={tableData}
            columns={columns}
            rowKey="key"
            pagination={false}
            size="small"
            scroll={{ x: 900 }}
          />
        ) : (
          <Text type="secondary">No scoring data available.</Text>
        )}
      </Card>

      {/* ---- Summary Description ---- */}
      {summary && (
        <Card title="Summary" style={{ marginTop: 16 }}>
          <Descriptions column={3} size="small">
            <Descriptions.Item label="Total Suites">{summary.total_suites}</Descriptions.Item>
            <Descriptions.Item label="Total Traces">{summary.total_traces}</Descriptions.Item>
            <Descriptions.Item label="Successful">{summary.success_count}</Descriptions.Item>
            <Descriptions.Item label="Failed">{summary.failed_count}</Descriptions.Item>
            <Descriptions.Item label="Avg Time">
              {summary.avg_time_per_trace_ms}ms
            </Descriptions.Item>
            <Descriptions.Item label="Total Time">
              {summary.total_time_ms}ms
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}

/* (c) 2026 AgentFlow-Eval */
/* Report detail — SaaS style radar + export */

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
  Alert,
  Statistic,
  Typography,
  Descriptions,
  Empty,
  message,
  Progress,
  Dropdown,
} from "antd";
import {
  DownloadOutlined,
  FileTextOutlined,
  ArrowLeftOutlined,
  EyeOutlined,
  CopyOutlined,
  BarChartOutlined,
  ShareAltOutlined,
  PrinterOutlined,
  FilePdfOutlined,
} from "@ant-design/icons";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from "recharts";
import { useTaskReport } from "@/hooks";
import type { TaskReport } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { exportReportPdf } from "@/utils/exportPdf";

const { Text, Paragraph } = Typography;

const DIMENSION_LABELS: Record<string, string> = {
  tool_accuracy: "工具准确率",
  answer_correctness: "答案正确性",
  reasoning_coherence: "推理连贯性",
};

const DIMENSION_MAX: Record<string, number> = {
  tool_accuracy: 40,
  answer_correctness: 40,
  reasoning_coherence: 20,
};

const DIM_COLORS = ["#38bdf8", "#34d399", "#818cf8"];

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
  const rows: string[] = [
    '"suite","status","tool_accuracy","answer_correctness","reasoning_coherence","total","tokens","time_ms"',
  ];
  for (const d of report.details || []) {
    for (const t of d.traces || []) {
      const scores = t.scores || {};
      const total = Object.values(scores).reduce((a: number, b: number) => a + b, 0);
      rows.push(
        [
          `"${(d.user_query || "").replace(/"/g, '""')}"`,
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
  const blob = new Blob([rows.join("\n")], { type: "text/csv;charset=utf-8" });
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

  const chartData = useMemo(() => {
    if (!report?.summary?.dimension_scores) return [];
    const ds = report.summary.dimension_scores;
    return Object.entries(DIMENSION_LABELS).map(([key, label]) => ({
      dimension: label,
      key,
      value: Math.round(((ds[key] || 0) / (DIMENSION_MAX[key] || 1)) * 100),
      raw: ds[key] || 0,
      max: DIMENSION_MAX[key] || 0,
    }));
  }, [report]);

  const handleExportJson = useCallback(() => {
    if (!report) return;
    exportJson(report, `report-${id}.json`);
    message.success("JSON 已导出");
  }, [report, id]);

  const handleExportCsv = useCallback(() => {
    if (!report) return;
    exportCsv(report);
    message.success("CSV 已导出");
  }, [report]);

  const handleExportPdf = useCallback(async () => {
    if (!report) return;
    try {
      message.loading({ content: "正在生成 PDF…", key: "pdf" });
      await exportReportPdf(report, `report-${id || report.task?.id}.pdf`);
      message.success({ content: "PDF 已下载", key: "pdf" });
    } catch (e) {
      console.error(e);
      message.error({ content: "PDF 生成失败", key: "pdf" });
    }
  }, [report, id]);

  const handleCopyJson = useCallback(async () => {
    if (!report) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
      message.success("报告 JSON 已复制到剪贴板");
    } catch {
      message.error("复制失败");
    }
  }, [report]);

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
          total: (Object.values(scores) as number[]).reduce((a: number, b: number) => a + b, 0),
          total_tokens: t.total_tokens,
          response_time_ms: t.response_time_ms,
          trace_id: t.trace_id,
        });
      }
    }
    return result;
  }, [report]);

  const columns = [
    {
      title: "用例",
      dataIndex: "user_query",
      key: "user_query",
      ellipsis: true,
      width: 260,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (s: string) => <StatusBadge status={s} />,
    },
    {
      title: "工具",
      dataIndex: "tool_accuracy",
      key: "tool_accuracy",
      width: 80,
      render: (v: number) => v ?? "-",
    },
    {
      title: "答案",
      dataIndex: "answer_correctness",
      key: "answer_correctness",
      width: 80,
      render: (v: number) => v ?? "-",
    },
    {
      title: "推理",
      dataIndex: "reasoning_coherence",
      key: "reasoning_coherence",
      width: 80,
      render: (v: number) => v ?? "-",
    },
    {
      title: "总分",
      dataIndex: "total",
      key: "total",
      width: 80,
      render: (v: number) => <Text strong>{typeof v === "number" ? Math.round(v) : v}</Text>,
    },
    {
      title: "Tokens",
      dataIndex: "total_tokens",
      key: "total_tokens",
      width: 90,
    },
    {
      title: "耗时",
      dataIndex: "response_time_ms",
      key: "response_time_ms",
      width: 90,
      render: (v: number) => (v != null ? `${v}ms` : "-"),
    },
    {
      title: "操作",
      key: "actions",
      width: 110,
      render: (_: unknown, record: { trace_id?: string }) =>
        record.trace_id ? (
          <Button
            size="small"
            type="link"
            icon={<EyeOutlined />}
            onClick={() => id && navigate(`/tasks/${id}`)}
          >
            轨迹
          </Button>
        ) : null,
    },
  ];

  if (isLoading) {
    return <PageSkeleton variant="report" />;
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="报告加载失败"
        description={(error as Error)?.message || "发生错误"}
        showIcon
        action={<Button onClick={() => refetch()}>重试</Button>}
      />
    );
  }

  if (!report) {
    return (
      <div className="af-glass" style={{ padding: 48, textAlign: "center" }}>
        <Empty description="暂无报告数据">
          <Button onClick={() => id && navigate(`/tasks/${id}`)}>返回任务</Button>
        </Empty>
      </div>
    );
  }

  const summary = report.summary;
  const overall = summary?.overall_score ?? 0;
  const passRate = summary?.total_traces
    ? Math.round((summary.success_count / summary.total_traces) * 100)
    : 0;

  return (
    <div className="ic-page af-page af-print-report">
      <div className="af-no-print">
        <PageHeader
          title="评测报告"
          subtitle={report.task?.name || id}
          icon={<BarChartOutlined />}
          extra={
            <Space wrap>
              <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/tasks/${id}`)}>
                返回任务
              </Button>
              <Button icon={<CopyOutlined />} onClick={handleCopyJson}>
                复制 JSON
              </Button>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: "json",
                      icon: <FileTextOutlined />,
                      label: "导出 JSON",
                      onClick: handleExportJson,
                    },
                    {
                      key: "csv",
                      icon: <DownloadOutlined />,
                      label: "导出 CSV",
                      onClick: handleExportCsv,
                    },
                    {
                      key: "pdf",
                      icon: <FilePdfOutlined />,
                      label: "导出 PDF（正式）",
                      onClick: () => {
                        void handleExportPdf();
                      },
                    },
                    {
                      key: "print",
                      icon: <PrinterOutlined />,
                      label: "浏览器打印",
                      onClick: () => {
                        message.info("请在打印对话框中选择「另存为 PDF」");
                        setTimeout(() => window.print(), 200);
                      },
                    },
                  ],
                }}
              >
                <Button
                  type="primary"
                  icon={<ShareAltOutlined />}
                  style={{ background: "var(--af-gradient)", border: "none" }}
                >
                  导出
                </Button>
              </Dropdown>
              <Button
                icon={<FilePdfOutlined />}
                onClick={() => {
                  void handleExportPdf();
                }}
              >
                下载 PDF
              </Button>
            </Space>
          }
        />
      </div>

      {/* Hero score */}
      <Card
        className="af-glass"
        styles={{ body: { padding: 22 } }}
        style={{
          marginBottom: 16,
          background: "var(--af-gradient-soft)",
        }}
      >
        <Row gutter={[24, 16]} align="middle">
          <Col xs={24} md={8} style={{ textAlign: "center" }}>
            <Progress
              type="dashboard"
              percent={Math.min(100, Math.round(overall))}
              size={150}
              strokeColor={{ "0%": "#38bdf8", "100%": "#818cf8" }}
              format={() => (
                <div>
                  <div style={{ fontSize: 32, fontWeight: 800 }}>{Math.round(overall)}</div>
                  <div style={{ fontSize: 12, color: "var(--af-text-muted)" }}>综合分</div>
                </div>
              )}
            />
          </Col>
          <Col xs={24} md={16}>
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic title="用例数" value={summary?.total_suites ?? 0} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="轨迹数" value={summary?.total_traces ?? 0} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="通过率" value={passRate} suffix="%" />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="总 Tokens" value={summary?.total_tokens ?? 0} />
              </Col>
            </Row>
            <Paragraph type="secondary" style={{ margin: "16px 0 0" }}>
              成功 {summary?.success_count ?? 0} · 失败 {summary?.failed_count ?? 0} · 均耗时{" "}
              {summary?.avg_time_per_trace_ms ?? 0}ms · 总耗时 {summary?.total_time_ms ?? 0}ms
            </Paragraph>
          </Col>
        </Row>
      </Card>

      {chartData.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card className="af-glass" title="维度雷达图" styles={{ body: { height: 320 } }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={chartData}>
                  <PolarGrid stroke="var(--af-border-strong)" />
                  <PolarAngleAxis
                    dataKey="dimension"
                    tick={{ fill: "var(--af-text-secondary)", fontSize: 12 }}
                  />
                  <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                  <Radar
                    dataKey="value"
                    stroke="#38bdf8"
                    fill="#818cf8"
                    fillOpacity={0.35}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card className="af-glass" title="维度得分明细">
              {chartData.map((d, i) => (
                <div key={d.dimension} style={{ marginBottom: 18 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <Text>{d.dimension}</Text>
                    <Text strong style={{ color: DIM_COLORS[i % DIM_COLORS.length] }}>
                      {d.raw} / {d.max}
                    </Text>
                  </div>
                  <Progress
                    percent={d.value}
                    showInfo={false}
                    strokeColor={DIM_COLORS[i % DIM_COLORS.length]}
                    trailColor="var(--af-bg-muted)"
                    size="small"
                  />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    占满分 {d.value}%
                  </Text>
                </div>
              ))}
            </Card>
          </Col>
        </Row>
      )}

      <Card className="af-glass" title="明细评分表" style={{ marginBottom: 16 }}>
        {tableData.length > 0 ? (
          <Table
            dataSource={tableData}
            columns={columns}
            rowKey="key"
            pagination={false}
            size="middle"
            scroll={{ x: 960 }}
          />
        ) : (
          <Empty description="暂无评分明细" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {summary && (
        <Card className="af-glass" title="汇总信息">
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
            <Descriptions.Item label="任务状态">
              <Tag>{report.task?.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="成功轨迹">{summary.success_count}</Descriptions.Item>
            <Descriptions.Item label="失败轨迹">{summary.failed_count}</Descriptions.Item>
            <Descriptions.Item label="平均耗时">{summary.avg_time_per_trace_ms}ms</Descriptions.Item>
            <Descriptions.Item label="总耗时">{summary.total_time_ms}ms</Descriptions.Item>
            <Descriptions.Item label="总 Tokens">{summary.total_tokens}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}

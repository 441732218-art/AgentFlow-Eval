import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Row,
  Col,
  Tag,
  Button,
  Space,
  Spin,
  Alert,
  Collapse,
  Descriptions,
  Modal,
  message,
  Statistic,
  Typography,
  Upload,
  Segmented,
} from "antd";
import {
  ReloadOutlined,
  PlayCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  BarChartOutlined,
  EyeOutlined,
  UploadOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import {
  useTaskDetail,
  useTaskReport,
  useExecuteTask,
  useCancelTask,
  useDeleteTask,
  useUploadTestSuites,
  useArchiveTask,
} from "@/hooks";
import { traceApi } from "@/api";
import TraceFlowChart from "@/components/TraceFlow/TraceFlowChart";
import ScoreCard from "@/components/TraceFlow/ScoreCard";
import StepLogPanel from "@/components/TraceFlow/StepLogPanel";
import type { Trace } from "@/types";
import { PageSkeleton } from "@/components/ui/PageSkeleton";

const { Text } = Typography;

function formatDate(date: string | null): string {
  if (!date) return "-";
  return new Date(date).toLocaleString("zh-CN");
}

const STATUS_COLORS: Record<string, string> = {
  created: "default",
  queued: "warning",
  running: "processing",
  waiting_tool: "warning",
  judging: "processing",
  completed: "success",
  failed: "error",
  cancelled: "default",
  timeout: "error",
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [traceView, setTraceView] = useState<"flow" | "timeline">("flow");

  // ---- Query task & report with polling when running ----
  // First load basic data to inspect status
  const tempTaskQuery = useTaskDetail(id, { enabled: !!id });
  const isRunning = tempTaskQuery.data && ["running", "queued", "judging"].includes(tempTaskQuery.data.status);

  const taskQuery = useTaskDetail(id, {
    refetchInterval: isRunning ? 3000 : false,
  });
  const reportQuery = useTaskReport(id, {
    refetchInterval: isRunning ? 3000 : false,
  });

  const executeMutation = useExecuteTask();
  const cancelMutation = useCancelTask();
  const deleteMutation = useDeleteTask();
  const uploadMutation = useUploadTestSuites(id || "");
  const archiveMutation = useArchiveTask();

  const task = taskQuery.data;
  const report = reportQuery.data;

  // ---- Actions ----
  const handleRefresh = () => {
    taskQuery.refetch();
    reportQuery.refetch();
  };

  const handleExecute = () => {
    if (!id) return;
    executeMutation.mutate(id, {
      onSuccess: () => {
        message.success("Task submitted for execution");
        taskQuery.refetch();
      },
      onError: () => message.error("Failed to execute task"),
    });
  };

  const handleCancel = () => {
    if (!id) return;
    cancelMutation.mutate(id, {
      onSuccess: () => {
        message.success("Cancellation request submitted");
        taskQuery.refetch();
      },
      onError: () => message.error("Failed to cancel task"),
    });
  };

  const handleDelete = () => {
    if (!id) return;
    Modal.confirm({
      title: "Delete Task",
      content: "Are you sure you want to delete this task? This action cannot be undone.",
      okText: "Delete",
      okType: "danger",
      onOk: () => {
        deleteMutation.mutate(id, {
          onSuccess: () => {
            message.success("Task deleted");
            navigate("/tasks");
          },
          onError: () => message.error("Failed to delete task"),
        });
      },
    });
  };

  const handleViewTrace = async (traceId: string) => {
    setTraceLoading(true);
    try {
      const trace = await traceApi.get(traceId);
      setSelectedTrace(trace);
    } catch {
      message.error("Failed to load trace");
    } finally {
      setTraceLoading(false);
    }
  };

  const handleUpload = (file: File) => {
    if (!id) return false;
    uploadMutation.mutate(file, {
      onSuccess: (res) => {
        message.success(res.message || `Imported ${res.created} suite(s)`);
        setUploadOpen(false);
        handleRefresh();
      },
      onError: (err: any) => {
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.error?.message ||
          err?.message ||
          "Upload failed";
        message.error(typeof msg === "string" ? msg : "Upload failed");
      },
    });
    return false;
  };

  const handleArchive = () => {
    if (!id) return;
    Modal.confirm({
      title: "Archive Task",
      content: "Archived tasks are hidden from the default list. Continue?",
      onOk: () =>
        archiveMutation.mutateAsync(id).then(() => {
          message.success("Task archived");
          navigate("/tasks");
        }),
    });
  };

  // ---- Loading ----
  if (taskQuery.isLoading) {
    return <PageSkeleton variant="detail" />;
  }

  // ---- Error ----
  if (taskQuery.error || !task) {
    return (
      <Alert
        type="error"
        message="Failed to load task"
        description={(taskQuery.error as Error)?.message || "Task not found"}
        showIcon
        action={<Button onClick={() => taskQuery.refetch()}>Retry</Button>}
      />
    );
  }

  // ---- Stats ----
  const totalSuites = report?.summary?.total_suites ?? task.test_suite_count ?? 0;
  const executed = report?.summary?.total_traces ?? 0;
  const avgScore = report?.summary?.overall_score ?? 0;
  const passRate =
    report?.summary?.total_traces && report.summary.total_traces > 0
      ? Math.round((report.summary.success_count / report.summary.total_traces) * 100)
      : 0;

  // ---- Collapse items ----
  const collapseItems = (report?.details || []).map((detail: { suite_id: string; user_query: string; expected_output: string; expected_tools: string[]; traces: Array<{ trace_id: string; status: string; total_tokens: number; response_time_ms: number; scores: Record<string, number>; created_at: string | null }> }, idx: number) => ({
    key: detail.suite_id || String(idx),
    label: (
      <Space>
        <Tag color={detail.traces?.[0]?.status === "success" ? "success" : "default"}>
          {detail.traces?.[0]?.status || "N/A"}
        </Tag>
        <Text ellipsis style={{ maxWidth: 400 }}>
          {detail.user_query.slice(0, 60)}...
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Score:{" "}
          {detail.traces?.[0]?.scores
            ? (Object.values(detail.traces[0].scores) as number[]).reduce((a: number, b: number) => a + b, 0)
            : "-"}
        </Text>
      </Space>
    ),
    children: (
      <div>
        <Descriptions size="small" column={2} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Query">{detail.user_query}</Descriptions.Item>
          <Descriptions.Item label="Expected Output">{detail.expected_output || "-"}</Descriptions.Item>
          <Descriptions.Item label="Expected Tools">
            {detail.expected_tools?.join(", ") || "-"}
          </Descriptions.Item>
        </Descriptions>
        {(detail.traces || []).map((t: { trace_id: string; status: string; total_tokens: number; response_time_ms: number; scores: Record<string, number>; created_at: string | null }) => (
          <Row key={t.trace_id} gutter={8} style={{ marginBottom: 8 }}>
            <Col span={3}>
              <Tag color={t.status === "success" ? "success" : "error"}>{t.status}</Tag>
            </Col>
            <Col span={3}>
              <Text style={{ fontSize: 12 }}>{t.total_tokens} tokens</Text>
            </Col>
            <Col span={3}>
              <Text style={{ fontSize: 12 }}>{t.response_time_ms}ms</Text>
            </Col>
            <Col span={5}>
              <Text style={{ fontSize: 12 }}>
                Score:{" "}
                {(Object.values(t.scores || {}) as number[]).reduce((a: number, b: number) => a + b, 0)}
              </Text>
            </Col>
            <Col span={4}>
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => handleViewTrace(t.trace_id)}
              >
                View Flow
              </Button>
            </Col>
          </Row>
        ))}
      </div>
    ),
  }));

  return (
    <div className="af-page">
      {/* ---- Header ---- */}
      <Card
        className="af-glass"
        styles={{ body: { padding: 20 } }}
        style={{ marginBottom: 16 }}
      >
        <Row justify="space-between" align="middle" gutter={[12, 12]}>
          <Col flex="auto">
            <Space size="middle" wrap>
              <Text strong style={{ fontSize: 20, letterSpacing: "-0.02em" }}>
                {task.name}
              </Text>
              <Tag color={STATUS_COLORS[task.status] || "default"}>{task.status}</Tag>
              <Tag color={task.created_by === "admin" ? "gold" : "processing"}>
                Owner: {task.created_by || "anonymous"}
              </Tag>
              {isRunning && (
                <Space size={6}>
                  <span className="af-live-dot" />
                  <Spin size="small" />
                </Space>
              )}
              <Text type="secondary" style={{ fontSize: 12 }}>
                Created: {formatDate(task.created_at)}
              </Text>
            </Space>
            {task.description && (
              <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
                {task.description}
              </Text>
            )}
          </Col>
          <Col>
            <Space wrap>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                刷新
              </Button>
              {task.status === "created" && (
                <Button icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>
                  导入用例
                </Button>
              )}
              {isRunning ? (
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  loading={cancelMutation.isPending}
                  onClick={handleCancel}
                >
                  取消
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  loading={executeMutation.isPending}
                  onClick={handleExecute}
                  disabled={task.status !== "created"}
                  style={
                    task.status === "created"
                      ? { background: "var(--af-gradient)", border: "none" }
                      : undefined
                  }
                >
                  执行
                </Button>
              )}
              {["completed", "failed", "cancelled", "timeout", "partial"].includes(task.status) && (
                <Button
                  icon={<BarChartOutlined />}
                  onClick={() => navigate(`/reports/${id}`)}
                >
                  报告
                </Button>
              )}
              {["completed", "failed", "cancelled", "timeout"].includes(task.status) &&
                !task.is_archived && (
                  <Button loading={archiveMutation.isPending} onClick={handleArchive}>
                    归档
                  </Button>
                )}
              <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
                删除
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      <Modal
        title="Import Test Suites (CSV / JSON)"
        open={uploadOpen}
        onCancel={() => setUploadOpen(false)}
        footer={null}
        destroyOnClose
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="CSV columns: user_query, expected_output, expected_tools"
          description="expected_tools can be comma/pipe-separated or a JSON array. JSON file should be an array of objects with the same fields."
        />
        <Upload.Dragger
          accept=".csv,.json,text/csv,application/json"
          multiple={false}
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploadMutation.isPending}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            {uploadMutation.isPending ? "Uploading..." : "Click or drag file to this area"}
          </p>
          <p className="ant-upload-hint">Supports .csv and .json (UTF-8)</p>
        </Upload.Dragger>
      </Modal>

      {/* ---- Stats Cards ---- */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        {[
          { title: "用例总数", value: totalSuites },
          { title: "已执行", value: `${executed} / ${totalSuites}` },
          { title: "平均分", value: avgScore, suffix: "/ 100" },
          { title: "通过率", value: passRate, suffix: "%" },
        ].map((s) => (
          <Col xs={12} md={6} key={s.title}>
            <Card className="af-glass" size="small" styles={{ body: { padding: 16 } }}>
              <Statistic title={s.title} value={s.value as number | string} suffix={s.suffix} />
            </Card>
          </Col>
        ))}
      </Row>

      {/* ---- Test Suites (Collapse) ---- */}
      {report?.details && report.details.length > 0 && (
        <Card className="af-glass" title="测试用例" style={{ marginBottom: 16 }}>
          <Collapse items={collapseItems} />
        </Card>
      )}

      {/* ---- Trace visualization ---- */}
      {selectedTrace && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={16}>
            <Card
              className="af-glass"
              title="执行轨迹"
              extra={
                <Space wrap>
                  <Segmented
                    size="small"
                    value={traceView}
                    onChange={(v) => setTraceView(v as "flow" | "timeline")}
                    options={[
                      { label: "流程图", value: "flow" },
                      { label: "时间线", value: "timeline" },
                    ]}
                  />
                  <Tag>Tokens: {selectedTrace.total_tokens}</Tag>
                  <Tag>{selectedTrace.response_time_ms}ms</Tag>
                  <Button size="small" onClick={() => setSelectedTrace(null)}>
                    关闭
                  </Button>
                </Space>
              }
            >
              {traceLoading ? (
                <div style={{ textAlign: "center", padding: 40 }}>
                  <Spin />
                </div>
              ) : traceView === "flow" ? (
                <TraceFlowChart steps={selectedTrace.steps} />
              ) : (
                <StepLogPanel steps={selectedTrace.steps} />
              )}
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <ScoreCard metricScores={selectedTrace.metric_scores || []} />
            {traceView === "flow" && (
              <Card
                className="af-glass"
                title="步骤摘要"
                size="small"
                style={{ marginTop: 16 }}
                styles={{ body: { maxHeight: 320, overflow: "auto" } }}
              >
                <StepLogPanel steps={selectedTrace.steps} />
              </Card>
            )}
          </Col>
        </Row>
      )}
    </div>
  );
}

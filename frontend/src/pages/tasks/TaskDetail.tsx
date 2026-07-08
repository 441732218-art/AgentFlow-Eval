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
} from "antd";
import {
  ReloadOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  BarChartOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import {
  useTaskDetail,
  useTaskReport,
  useExecuteTask,
  useDeleteTask,
} from "@/hooks";
import { traceApi } from "@/api";
import TraceFlowChart from "@/pages/TaskDetail/components/TraceFlowChart";
import ScoreCard from "@/pages/TaskDetail/components/ScoreCard";
import StepLogPanel from "@/pages/TaskDetail/components/StepLogPanel";
import type { Trace } from "@/types";

const { Text } = Typography;

function formatDate(date: string | null): string {
  if (!date) return "-";
  return new Date(date).toLocaleString("zh-CN");
}

const STATUS_COLORS: Record<string, string> = {
  pending: "default",
  running: "processing",
  completed: "success",
  failed: "error",
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const taskQuery = useTaskDetail(id);
  const reportQuery = useTaskReport(id);
  const executeMutation = useExecuteTask();
  const deleteMutation = useDeleteTask();

  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [traceLoading, setTraceLoading] = useState(false);

  const task = taskQuery.data;
  const report = reportQuery.data;

  // ---- Polling ----
  const isRunning = task?.status === "pending" || task?.status === "running";

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

  // ---- Loading ----
  if (taskQuery.isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 80 }}>
        <Spin size="large" />
      </div>
    );
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
  const collapseItems = (report?.details || []).map((detail, idx) => ({
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
            ? Object.values(detail.traces[0].scores).reduce((a: number, b: number) => a + b, 0)
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
        {(detail.traces || []).map((t) => (
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
                {Object.values(t.scores || {}).reduce((a: number, b: number) => a + b, 0)}
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
    <div>
      {/* ---- Header ---- */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space size="middle">
              <Text strong style={{ fontSize: 18 }}>
                {task.name}
              </Text>
              <Tag color={STATUS_COLORS[task.status] || "default"}>{task.status}</Tag>
              {isRunning && <Spin size="small" />}
              <Text type="secondary" style={{ fontSize: 12 }}>
                Created: {formatDate(task.created_at)}
              </Text>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                Refresh
              </Button>
              {task.status === "pending" && (
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  loading={executeMutation.isPending}
                  onClick={handleExecute}
                >
                  Execute
                </Button>
              )}
              {task.status === "completed" && (
                <Button
                  icon={<BarChartOutlined />}
                  onClick={() => navigate(`/reports/${id}`)}
                >
                  View Report
                </Button>
              )}
              <Button danger icon={<DeleteOutlined />} onClick={handleDelete}>
                Delete
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* ---- Stats Cards ---- */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Total Suites" value={totalSuites} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Executed" value={`${executed} / ${totalSuites}`} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Average Score" value={avgScore} suffix="/ 100" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Pass Rate" value={passRate} suffix="%" />
          </Card>
        </Col>
      </Row>

      {/* ---- Test Suites (Collapse) ---- */}
      {report?.details && report.details.length > 0 && (
        <Card title="Test Suites" style={{ marginBottom: 16 }}>
          <Collapse items={collapseItems} />
        </Card>
      )}

      {/* ---- Trace Flow Chart ---- */}
      {selectedTrace && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={16}>
            <Card
              title="Execution Flow"
              extra={
                <Button
                  size="small"
                  onClick={() => setSelectedTrace(null)}
                >
                  Close
                </Button>
              }
            >
              {traceLoading ? (
                <Spin />
              ) : (
                <TraceFlowChart steps={selectedTrace.steps} />
              )}
            </Card>
          </Col>
          <Col span={8}>
            <ScoreCard metricScores={selectedTrace.metric_scores || []} />
          </Col>
        </Row>
      )}

      {/* ---- Step Log ---- */}
      {selectedTrace && (
        <Card
          title="Execution Steps"
          extra={
            <Space>
              <Tag>Tokens: {selectedTrace.total_tokens}</Tag>
              <Tag>Time: {selectedTrace.response_time_ms}ms</Tag>
            </Space>
          }
          style={{ marginBottom: 16 }}
        >
          <StepLogPanel steps={selectedTrace.steps} />
        </Card>
      )}
    </div>
  );
}

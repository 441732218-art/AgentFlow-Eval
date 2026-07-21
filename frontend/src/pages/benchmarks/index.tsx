/* (c) 2026 AgentFlow-Eval — Continuous Evaluation (Phase 4) */

import React, { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  PlusOutlined,
  PlayCircleOutlined,
  TrophyOutlined,
  ReloadOutlined,
  ExperimentOutlined,
  DiffOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import {
  benchmarksApi,
  type Benchmark,
  type BenchmarkRun,
  type LeaderboardRow,
  type RunComparison,
} from "@/api";
import { Can } from "@/auth";
import { formatDateTime } from "@/utils/format";

const { Text, Paragraph, Title } = Typography;
const { TextArea } = Input;

const BENCH_KEY = ["benchmarks"] as const;

function fmtNum(v: unknown, digits = 2): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(digits) : "—";
}

function fmtPct(v: unknown): string {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function verdictTag(verdict: RunComparison["verdict"]) {
  const map: Record<
    RunComparison["verdict"],
    { color: string; icon: React.ReactNode; label: string }
  > = {
    improved: {
      color: "success",
      icon: <ArrowUpOutlined />,
      label: "提升",
    },
    stable: {
      color: "default",
      icon: <MinusOutlined />,
      label: "持平",
    },
    regressed: {
      color: "error",
      icon: <ArrowDownOutlined />,
      label: "下降",
    },
    unknown: {
      color: "warning",
      icon: <MinusOutlined />,
      label: "未知",
    },
  };
  const m = map[verdict] || map.unknown;
  return (
    <Tag color={m.color} icon={m.icon}>
      {m.label}
    </Tag>
  );
}

function deltaColor(d: number | null | undefined): string | undefined {
  if (d == null) return undefined;
  if (d > 0) return "#16a34a";
  if (d < 0) return "#dc2626";
  return undefined;
}

const BenchmarksPage: React.FC = () => {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [runOpen, setRunOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareResult, setCompareResult] = useState<RunComparison | null>(null);
  const [form] = Form.useForm();
  const [runForm] = Form.useForm();
  const [compareForm] = Form.useForm();

  const listQ = useQuery({
    queryKey: BENCH_KEY,
    queryFn: () => benchmarksApi.list(),
  });

  const detailQ = useQuery({
    queryKey: [...BENCH_KEY, selectedId],
    queryFn: () => benchmarksApi.get(selectedId!),
    enabled: !!selectedId,
  });

  const runsQ = useQuery({
    queryKey: [...BENCH_KEY, selectedId, "runs"],
    queryFn: () => benchmarksApi.listRuns(selectedId!),
    enabled: !!selectedId,
    refetchInterval: (q) => {
      const items = q.state.data?.items ?? [];
      return items.some((r) =>
        ["queued", "running", "pending"].includes(r.status)
      )
        ? 4000
        : false;
    },
  });

  const boardQ = useQuery({
    queryKey: [...BENCH_KEY, selectedId, "leaderboard"],
    queryFn: () => benchmarksApi.leaderboard(selectedId!),
    enabled: !!selectedId,
  });

  const invalidateSelected = () => {
    void qc.invalidateQueries({ queryKey: [...BENCH_KEY, selectedId] });
    void qc.invalidateQueries({ queryKey: [...BENCH_KEY, selectedId, "runs"] });
    void qc.invalidateQueries({
      queryKey: [...BENCH_KEY, selectedId, "leaderboard"],
    });
  };

  const createMut = useMutation({
    mutationFn: benchmarksApi.create,
    onSuccess: (bm) => {
      message.success("Benchmark 已创建");
      setCreateOpen(false);
      form.resetFields();
      void qc.invalidateQueries({ queryKey: BENCH_KEY });
      setSelectedId(bm.id);
    },
    onError: (e: Error) => message.error(e.message),
  });

  const runMut = useMutation({
    mutationFn: (vars: {
      id: string;
      label: string;
      agent_config: Record<string, unknown>;
    }) =>
      benchmarksApi.run(vars.id, {
        label: vars.label,
        agent_config: vars.agent_config,
        enqueue: true,
      }),
    onSuccess: (data) => {
      message.success(`试跑已提交 · task=${data.run.task_id || "—"}`);
      setRunOpen(false);
      runForm.resetFields();
      invalidateSelected();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const finalizeMut = useMutation({
    mutationFn: (runId: string) =>
      benchmarksApi.finalizeRun(selectedId!, runId),
    onSuccess: () => {
      message.success("已刷新试跑结果");
      invalidateSelected();
    },
    onError: (e: Error) => message.error(e.message),
  });

  const compareMut = useMutation({
    mutationFn: (body: {
      current_run_id: string;
      baseline_run_id?: string;
      score_stable_eps?: number;
    }) => benchmarksApi.compare(selectedId!, body),
    onSuccess: (data) => {
      setCompareResult(data);
      message.success(data.headline || "对比完成");
    },
    onError: (e: Error) => message.error(e.message),
  });

  const items = listQ.data?.items ?? [];
  const runs: BenchmarkRun[] = runsQ.data?.items ?? [];
  const board: LeaderboardRow[] = boardQ.data?.items ?? [];

  const runOptions = useMemo(
    () =>
      runs.map((r) => ({
        value: r.id,
        label: `${r.label} · ${r.status} · score=${fmtNum(r.summary?.score)} · ${r.id.slice(0, 8)}`,
      })),
    [runs]
  );

  const boardCols = useMemo(
    () => [
      { title: "#", dataIndex: "rank", width: 56 },
      { title: "Label", dataIndex: "label" },
      {
        title: "Score",
        dataIndex: "score",
        render: (v: number | null | undefined) => fmtNum(v),
      },
      {
        title: "Accuracy",
        dataIndex: "accuracy",
        render: (v: number | null | undefined) => fmtNum(v),
      },
      {
        title: "Quality",
        dataIndex: "quality",
        render: (v: number | null | undefined) => fmtNum(v),
      },
      {
        title: "Latency ms",
        dataIndex: "latency_ms",
        render: (v: number | null | undefined) => fmtNum(v, 0),
      },
      {
        title: "Status",
        dataIndex: "status",
        render: (s: string) => <Tag>{s}</Tag>,
      },
    ],
    []
  );

  const runCols = useMemo(
    () => [
      {
        title: "Label",
        dataIndex: "label",
        width: 120,
      },
      {
        title: "Status",
        dataIndex: "status",
        width: 100,
        render: (s: string) => {
          const color =
            s === "completed"
              ? "success"
              : s === "failed"
                ? "error"
                : s === "running" || s === "queued"
                  ? "processing"
                  : "default";
          return <Tag color={color}>{s}</Tag>;
        },
      },
      {
        title: "Score",
        key: "score",
        width: 80,
        render: (_: unknown, r: BenchmarkRun) => fmtNum(r.summary?.score),
      },
      {
        title: "成功率",
        key: "sr",
        width: 90,
        render: (_: unknown, r: BenchmarkRun) =>
          fmtPct(r.summary?.success_rate),
      },
      {
        title: "覆盖",
        key: "cov",
        width: 80,
        render: (_: unknown, r: BenchmarkRun) =>
          fmtPct(r.summary?.score_coverage),
      },
      {
        title: "Task",
        dataIndex: "task_id",
        width: 100,
        render: (tid: string | null | undefined) =>
          tid ? (
            <Link to={`/tasks/${tid}`}>{tid.slice(0, 8)}…</Link>
          ) : (
            "—"
          ),
      },
      {
        title: "时间",
        dataIndex: "created_at",
        width: 160,
        render: (v: string | null | undefined) =>
          v ? formatDateTime(v) : "—",
      },
      {
        title: "操作",
        key: "actions",
        width: 160,
        render: (_: unknown, r: BenchmarkRun) => (
          <Space size="small">
            <Button
              type="link"
              size="small"
              loading={finalizeMut.isPending}
              onClick={() => finalizeMut.mutate(r.id)}
            >
              刷新
            </Button>
            <Button
              type="link"
              size="small"
              icon={<DiffOutlined />}
              onClick={() => {
                compareForm.setFieldsValue({
                  current_run_id: r.id,
                  baseline_run_id: undefined,
                });
                setCompareResult(null);
                setCompareOpen(true);
              }}
            >
              对比
            </Button>
          </Space>
        ),
      },
    ],
    [compareForm, finalizeMut]
  );

  if (listQ.isLoading) return <PageSkeleton variant="cards" />;

  return (
    <div className="ic-page">
      <PageHeader
        title="持续评测"
        subtitle="Benchmark 基准 · 回归试跑 · 退化检测（Phase 4）"
        icon={<ExperimentOutlined />}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void listQ.refetch()}
            >
              刷新
            </Button>
            <Can perm="benchmark:create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateOpen(true)}
              >
                新建 Benchmark
              </Button>
            </Can>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="Continuous Evaluation：固定基准用例 + 手动试跑 + 与基线对比"
        description="改提示 / 换模型 / 调工具后，对同一 Benchmark 再跑一次，即可看到平均分、维度分、成功率是否退化。复用现有 Task / Scorecard / Evaluation Engine，不引入第二套执行引擎。"
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="Benchmark 列表" size="small">
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={items}
              onRow={(row: Benchmark) => ({
                onClick: () => {
                  setSelectedId(row.id);
                  setCompareResult(null);
                },
                style: {
                  cursor: "pointer",
                  background:
                    row.id === selectedId
                      ? "var(--af-primary-soft, rgba(56,189,248,0.08))"
                      : undefined,
                },
              })}
              columns={[
                {
                  title: "名称",
                  dataIndex: "name",
                  render: (name: string, row: Benchmark) => (
                    <Space direction="vertical" size={0}>
                      <Text>{name}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        v{row.version || "1.0"} · {row.case_count ?? "—"} cases
                      </Text>
                    </Space>
                  ),
                },
              ]}
              locale={{ emptyText: "暂无 Benchmark，请先创建" }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          {!selectedId ? (
            <Card>
              <Paragraph type="secondary">
                选择左侧 Benchmark 查看详情、历史试跑与退化对比
              </Paragraph>
            </Card>
          ) : (
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              <Card
                title={detailQ.data?.name || selectedId}
                loading={detailQ.isLoading}
                extra={
                  <Space>
                    <Can perm="benchmark:create">
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={() => {
                          runForm.setFieldsValue({
                            label: `run-${new Date().toISOString().slice(0, 10)}`,
                            runner: "openai",
                            model: "gpt-4o-mini",
                            temperature: 0,
                          });
                          setRunOpen(true);
                        }}
                      >
                        触发试跑
                      </Button>
                    </Can>
                    <Button
                      icon={<DiffOutlined />}
                      disabled={runs.length < 1}
                      onClick={() => {
                        const latest = runs[0];
                        compareForm.setFieldsValue({
                          current_run_id: latest?.id,
                          baseline_run_id: runs[1]?.id,
                        });
                        setCompareResult(null);
                        setCompareOpen(true);
                      }}
                    >
                      对比试跑
                    </Button>
                  </Space>
                }
              >
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="版本">
                    {detailQ.data?.version || "1.0"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Cases">
                    {detailQ.data?.case_count ??
                      detailQ.data?.cases?.length ??
                      0}
                  </Descriptions.Item>
                  <Descriptions.Item label="Scorecard">
                    {detailQ.data?.scorecard ? (
                      <Tag color="blue" icon={<CheckCircleOutlined />}>
                        已绑定
                      </Tag>
                    ) : (
                      <Text type="secondary">默认 / 未绑定</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="来源 Task">
                    {detailQ.data?.source_task_id ? (
                      <Link to={`/tasks/${detailQ.data.source_task_id}`}>
                        {detailQ.data.source_task_id.slice(0, 8)}…
                      </Link>
                    ) : (
                      "—"
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>
                    <Text type="secondary">
                      {detailQ.data?.description || "—"}
                    </Text>
                  </Descriptions.Item>
                </Descriptions>
                {(detailQ.data?.cases?.length ?? 0) > 0 && (
                  <Table
                    style={{ marginTop: 12 }}
                    size="small"
                    rowKey={(r) => r.id || r.user_query}
                    pagination={{ pageSize: 5 }}
                    dataSource={detailQ.data?.cases || []}
                    columns={[
                      { title: "Name", dataIndex: "name", width: 120 },
                      {
                        title: "Query",
                        dataIndex: "user_query",
                        ellipsis: true,
                      },
                      {
                        title: "Expected",
                        dataIndex: "expected_output",
                        ellipsis: true,
                      },
                    ]}
                  />
                )}
              </Card>

              <Card
                title={
                  <Space>
                    <HistoryOutlined /> 历史试跑
                  </Space>
                }
                loading={runsQ.isLoading}
                extra={
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => void runsQ.refetch()}
                  >
                    刷新
                  </Button>
                }
              >
                <Table
                  size="small"
                  rowKey="id"
                  dataSource={runs}
                  columns={runCols}
                  pagination={{ pageSize: 8 }}
                  locale={{
                    emptyText: "暂无试跑 — 点击「触发试跑」开始回归评测",
                  }}
                  scroll={{ x: 800 }}
                />
              </Card>

              {compareResult && (
                <Card
                  title={
                    <Space>
                      <DiffOutlined /> 退化检测
                      {verdictTag(compareResult.verdict)}
                    </Space>
                  }
                >
                  <Paragraph>{compareResult.headline}</Paragraph>
                  <Row gutter={16}>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="Δ Score"
                        value={compareResult.score_delta ?? "—"}
                        precision={
                          compareResult.score_delta != null ? 2 : undefined
                        }
                        valueStyle={{
                          color: deltaColor(compareResult.score_delta),
                        }}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="Δ 成功率"
                        value={
                          compareResult.success_rate_delta != null
                            ? (
                                compareResult.success_rate_delta * 100
                              ).toFixed(1) + "%"
                            : "—"
                        }
                        valueStyle={{
                          color: deltaColor(
                            compareResult.success_rate_delta
                          ),
                        }}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="Δ 评分覆盖"
                        value={
                          compareResult.score_coverage_delta != null
                            ? (
                                compareResult.score_coverage_delta * 100
                              ).toFixed(1) + "%"
                            : "—"
                        }
                        valueStyle={{
                          color: deltaColor(
                            compareResult.score_coverage_delta
                          ),
                        }}
                      />
                    </Col>
                    <Col xs={12} sm={6}>
                      <Statistic
                        title="当前总分"
                        value={fmtNum(
                          compareResult.current?.summary?.score
                        )}
                      />
                    </Col>
                  </Row>
                  <Title level={5} style={{ marginTop: 16 }}>
                    维度变化
                  </Title>
                  <Table
                    size="small"
                    rowKey="dimension"
                    pagination={false}
                    dataSource={Object.entries(
                      compareResult.dimension_deltas || {}
                    ).map(([dimension, delta]) => ({
                      dimension,
                      delta,
                      current:
                        (
                          compareResult.current?.summary
                            ?.dimension_scores as Record<string, number>
                        )?.[dimension] ?? null,
                      baseline:
                        (
                          compareResult.baseline?.summary
                            ?.dimension_scores as Record<string, number>
                        )?.[dimension] ?? null,
                    }))}
                    columns={[
                      { title: "维度", dataIndex: "dimension" },
                      {
                        title: "基线",
                        dataIndex: "baseline",
                        render: (v: number | null) => fmtNum(v),
                      },
                      {
                        title: "当前",
                        dataIndex: "current",
                        render: (v: number | null) => fmtNum(v),
                      },
                      {
                        title: "Δ",
                        dataIndex: "delta",
                        render: (d: number | null) => (
                          <Text style={{ color: deltaColor(d) }}>
                            {d == null ? "—" : `${d >= 0 ? "+" : ""}${fmtNum(d)}`}
                          </Text>
                        ),
                      },
                    ]}
                    locale={{ emptyText: "无维度分数据" }}
                  />
                  <Paragraph type="secondary" style={{ marginTop: 12 }}>
                    当前: {compareResult.current?.label} (
                    {compareResult.current?.run_id?.slice(0, 8)}) · 基线:{" "}
                    {compareResult.baseline?.label} (
                    {compareResult.baseline?.run_id?.slice(0, 8)})
                  </Paragraph>
                </Card>
              )}

              <Card
                title={
                  <Space>
                    <TrophyOutlined /> 排行榜（按 label）
                  </Space>
                }
                loading={boardQ.isLoading}
                extra={
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => void boardQ.refetch()}
                  >
                    刷新
                  </Button>
                }
              >
                <Table
                  size="small"
                  rowKey="run_id"
                  dataSource={board}
                  columns={boardCols}
                  pagination={false}
                  locale={{
                    emptyText: "暂无已完成 Run — 试跑并 finalize 后上榜",
                  }}
                />
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      {/* Create Benchmark */}
      <Modal
        title="新建 Benchmark（评测基准）"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMut.isPending}
        destroyOnClose
        width={560}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ version: "1.0" }}
          onFinish={(values) => {
            let cases: Array<{
              user_query: string;
              expected_output?: string;
            }> = [];
            const raw = (values.cases_json || "").trim();
            if (raw) {
              try {
                const parsed = JSON.parse(raw);
                cases = Array.isArray(parsed)
                  ? parsed
                  : parsed.cases || parsed.items || [];
              } catch {
                message.error("Cases JSON 无法解析");
                return;
              }
            }
            let scorecard: Record<string, unknown> | undefined;
            const scRaw = (values.scorecard_json || "").trim();
            if (scRaw) {
              try {
                scorecard = JSON.parse(scRaw);
              } catch {
                message.error("Scorecard JSON 无法解析");
                return;
              }
            }
            createMut.mutate({
              name: values.name,
              description: values.description || "",
              version: values.version || "1.0",
              cases: values.source_task_id ? undefined : cases,
              source_task_id: values.source_task_id || undefined,
              scorecard,
            });
          }}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="e.g. Tool-Use Bench v1" />
          </Form.Item>
          <Form.Item name="version" label="版本">
            <Input placeholder="1.0" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="source_task_id"
            label="从 Task 生成（可选）"
            extra="填写已有 Task ID 时，将克隆其 TestSuite 为固定用例"
          >
            <Input placeholder="task uuid" />
          </Form.Item>
          <Form.Item
            name="cases_json"
            label="Cases (JSON 数组，可选)"
            extra='示例: [{"user_query":"hi","expected_output":"hello"}]'
          >
            <TextArea rows={5} placeholder="[]" />
          </Form.Item>
          <Form.Item
            name="scorecard_json"
            label="默认 Scorecard (JSON，可选)"
            extra="绑定后试跑会写入 agent_config.scorecard"
          >
            <TextArea rows={3} placeholder="留空使用系统默认" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Trigger run */}
      <Modal
        title="触发回归试跑"
        open={runOpen}
        onCancel={() => setRunOpen(false)}
        onOk={() => runForm.submit()}
        confirmLoading={runMut.isPending}
        destroyOnClose
        okText="提交试跑"
      >
        <Form
          form={runForm}
          layout="vertical"
          onFinish={(values) => {
            if (!selectedId) return;
            const agent_config: Record<string, unknown> = {
              runner: values.runner || "openai",
              model: values.model || "gpt-4o-mini",
              temperature: Number(values.temperature ?? 0),
            };
            if (values.endpoint_url) {
              agent_config.endpoint_url = values.endpoint_url;
              agent_config.runner = "http";
            }
            runMut.mutate({
              id: selectedId,
              label: values.label || "default",
              agent_config,
            });
          }}
        >
          <Form.Item
            name="label"
            label="试跑标签"
            rules={[{ required: true }]}
            extra="用于排行榜分组与对比识别"
          >
            <Input placeholder="baseline / prompt-v2 / model-b" />
          </Form.Item>
          <Form.Item name="runner" label="Runner" initialValue="openai">
            <Select
              options={[
                { value: "openai", label: "openai" },
                { value: "http", label: "http (HttpAgentRunner)" },
                { value: "mock", label: "mock" },
              ]}
            />
          </Form.Item>
          <Form.Item name="model" label="模型" initialValue="gpt-4o-mini">
            <Input />
          </Form.Item>
          <Form.Item name="temperature" label="Temperature" initialValue={0}>
            <Input type="number" step={0.1} />
          </Form.Item>
          <Form.Item
            name="endpoint_url"
            label="HTTP endpoint（可选）"
            extra="填写后 runner 自动设为 http"
          >
            <Input placeholder="https://..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Compare runs */}
      <Modal
        title="对比试跑（退化检测）"
        open={compareOpen}
        onCancel={() => setCompareOpen(false)}
        onOk={() => compareForm.submit()}
        confirmLoading={compareMut.isPending}
        destroyOnClose
        okText="开始对比"
        width={520}
      >
        <Form
          form={compareForm}
          layout="vertical"
          onFinish={(values) => {
            compareMut.mutate({
              current_run_id: values.current_run_id,
              baseline_run_id: values.baseline_run_id || undefined,
              score_stable_eps: Number(values.score_stable_eps ?? 1),
            });
            setCompareOpen(false);
          }}
        >
          <Form.Item
            name="current_run_id"
            label="当前试跑"
            rules={[{ required: true, message: "请选择当前试跑" }]}
          >
            <Select options={runOptions} placeholder="选择 run" />
          </Form.Item>
          <Form.Item
            name="baseline_run_id"
            label="基线试跑"
            extra="留空则自动取当前之前最近一次可比较试跑"
          >
            <Select
              allowClear
              options={runOptions}
              placeholder="自动 / 手动选择"
            />
          </Form.Item>
          <Form.Item
            name="score_stable_eps"
            label="持平阈值 |Δscore|"
            initialValue={1}
          >
            <Input type="number" min={0} step={0.5} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BenchmarksPage;

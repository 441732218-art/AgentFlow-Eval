/* LangSmith-style Trace Explorer — tree + detail + DAG + metrics */

import { useEffect, useMemo, useState } from "react";
import {
  Input,
  Select,
  Space,
  Tag,
  Empty,
  Spin,
  Typography,
  Descriptions,
  Divider,
  Button,
  Segmented,
  Progress,
  Tooltip,
  message,
} from "antd";
import {
  SearchOutlined,
  ApartmentOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  BugOutlined,
  NodeIndexOutlined,
  UnorderedListOutlined,
  BarChartOutlined,
  ExperimentOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTraces, useTraceDetail, useJudgeTrace } from "@/hooks";
import { Panel } from "@/components/widgets/Panel";
import { MetricCard } from "@/components/widgets/MetricCard";
import { EChart, buildBarOption, buildLineOption, CHART_COLORS } from "@/components/charts/EChart";
import TraceFlowChart from "@/components/TraceFlow/TraceFlowChart";
import { formatDateTime } from "@/utils/format";
import { shortId, stepBody, stepKind, stepLabel } from "@/lib/observability";
import type { Trace, TraceStep } from "@/types";

const { Text, Paragraph } = Typography;

type DetailTab = "steps" | "dag" | "metrics";

function TraceTree({
  traces,
  selectedId,
  activeStep,
  onSelect,
  onStepClick,
}: {
  traces: Trace[];
  selectedId?: string;
  activeStep?: number;
  onSelect: (id: string) => void;
  onStepClick: (idx: number) => void;
}) {
  return (
    <div>
      {traces.map((tr) => {
        const open = selectedId === tr.id;
        return (
          <div key={tr.id} style={{ marginBottom: 10 }}>
            <div
              className={`ic-tree-item ${open ? "is-active" : ""}`}
              onClick={() => onSelect(tr.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <Text strong className="ic-mono" style={{ fontSize: 12 }}>
                  {shortId(tr.id)}
                </Text>
                <Tag color={tr.status === "success" ? "success" : "error"}>{tr.status}</Tag>
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--af-text-secondary)",
                  marginTop: 4,
                  lineHeight: 1.4,
                }}
              >
                {(tr.user_query || "").slice(0, 80)}
                {(tr.user_query || "").length > 80 ? "…" : ""}
              </div>
              <div style={{ marginTop: 6, fontSize: 11, color: "var(--af-text-muted)" }}>
                <ThunderboltOutlined /> {(tr.total_tokens ?? 0).toLocaleString()} tok ·{" "}
                <ClockCircleOutlined /> {tr.response_time_ms ?? 0} ms
                {tr.model_version ? (
                  <>
                    {" "}
                    · <span className="ic-mono">{tr.model_version}</span>
                  </>
                ) : null}
              </div>
            </div>
            {open && (tr.steps?.length || 0) > 0 ? (
              <div
                style={{
                  paddingLeft: 12,
                  borderLeft: "1px solid var(--af-border)",
                  marginLeft: 12,
                  marginTop: 4,
                }}
              >
                {(tr.steps || []).slice(0, 24).map((s, i) => (
                  <div
                    key={i}
                    className={`ic-tree-item ${activeStep === i ? "is-active" : ""}`}
                    style={{ padding: "4px 8px", fontSize: 11 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onStepClick(i);
                    }}
                  >
                    <span style={{ color: "var(--af-text-muted)" }}>└ </span>
                    <Tag
                      style={{ fontSize: 10, marginInlineEnd: 4, lineHeight: "16px" }}
                      color={
                        stepKind(s) === "action"
                          ? "gold"
                          : stepKind(s) === "observation"
                            ? "success"
                            : stepKind(s) === "final_answer"
                              ? "purple"
                              : "blue"
                      }
                    >
                      {stepKind(s)}
                    </Tag>
                    {stepLabel(s, i).slice(0, 42)}
                  </div>
                ))}
                {(tr.steps?.length || 0) > 24 ? (
                  <Text type="secondary" style={{ fontSize: 11, paddingLeft: 8 }}>
                    +{(tr.steps?.length || 0) - 24} more steps
                  </Text>
                ) : null}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export default function TraceExplorerPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("id") || undefined;
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<string | undefined>();
  const [sort, setSort] = useState<"newest" | "oldest" | "latency" | "tokens">("newest");
  const [tab, setTab] = useState<DetailTab>("steps");
  const [activeStep, setActiveStep] = useState<number | undefined>();

  const { data, isLoading, refetch } = useTraces({ page: 1, page_size: 80 });
  const { data: detail, isLoading: detailLoading } = useTraceDetail(selectedId);
  const judgeMut = useJudgeTrace();

  const filtered = useMemo(() => {
    let items = data?.items ?? [];
    if (status) items = items.filter((t) => t.status === status);
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      items = items.filter(
        (t) =>
          t.id.toLowerCase().includes(needle) ||
          (t.user_query || "").toLowerCase().includes(needle) ||
          (t.model_version || "").toLowerCase().includes(needle) ||
          (t.agent_version || "").toLowerCase().includes(needle) ||
          (t.prompt_version || "").toLowerCase().includes(needle)
      );
    }
    const sorted = [...items];
    sorted.sort((a, b) => {
      if (sort === "oldest") return (a.created_at || "").localeCompare(b.created_at || "");
      if (sort === "latency") return (b.response_time_ms || 0) - (a.response_time_ms || 0);
      if (sort === "tokens") return (b.total_tokens || 0) - (a.total_tokens || 0);
      return (b.created_at || "").localeCompare(a.created_at || "");
    });
    return sorted;
  }, [data, q, status, sort]);

  // Auto-select first trace when none selected
  useEffect(() => {
    if (!selectedId && filtered.length > 0) {
      setParams({ id: filtered[0].id }, { replace: true });
    }
  }, [selectedId, filtered, setParams]);

  useEffect(() => {
    setActiveStep(undefined);
    setTab("steps");
  }, [selectedId]);

  const select = (id: string) => setParams({ id });

  const active: Trace | undefined =
    detail || filtered.find((t) => t.id === selectedId);

  const stepTokenSeries = useMemo(() => {
    const steps = active?.steps || [];
    return buildLineOption([
      {
        name: "Step tokens",
        color: CHART_COLORS.warning,
        data: steps.map((s, i) => ({
          t: `#${i + 1}`,
          v: Number(s.tokens || 0),
        })),
      },
    ]);
  }, [active]);

  const scoreBar = useMemo(() => {
    const scores = active?.metric_scores || [];
    return buildBarOption(
      scores.map((ms) => ({ name: ms.metric_name, value: ms.score })),
      { horizontal: true }
    );
  }, [active]);

  const copyId = async () => {
    if (!active?.id) return;
    try {
      await navigator.clipboard.writeText(active.id);
      message.success("Trace ID 已复制");
    } catch {
      message.info(active.id);
    }
  };

  const onJudge = () => {
    if (!active?.id) return;
    judgeMut.mutate(active.id, {
      onSuccess: () => {
        message.success("Judge 完成");
        void refetch();
      },
      onError: (e: Error) => message.error(e.message),
    });
  };

  return (
    <div className="ic-page">
      <div className="ic-page-header">
        <div className="ic-page-header__main">
          <div className="ic-page-header__icon">
            <ApartmentOutlined />
          </div>
          <div>
            <div className="ic-page-header__title-row">
              <h1 className="af-section-title" style={{ margin: 0 }}>
                Trace Explorer
              </h1>
              <span className="ic-live-badge">
                <span className="af-live-dot" /> Live
              </span>
            </div>
            <p className="af-section-sub" style={{ margin: "4px 0 0" }}>
              LangSmith 风格 · Tree / DAG / Metrics · 版本与 Token 全链路
            </p>
          </div>
        </div>
        <div className="ic-page-header__extra">
          <Space wrap>
            <Button onClick={() => void refetch()}>刷新</Button>
            <Button icon={<BugOutlined />} onClick={() => navigate("/diagnosis")}>
              Diagnosis
            </Button>
          </Space>
        </div>
      </div>

      <div className="ic-split">
        <Panel
          title={
            <>
              <ApartmentOutlined /> Trace Tree
            </>
          }
          extra={<Tag>{filtered.length}</Tag>}
          bodyStyle={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}
        >
          <Space direction="vertical" style={{ width: "100%", marginBottom: 12 }} size={8}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜索 query / id / model / prompt…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <Space wrap>
              <Select
                allowClear
                placeholder="状态"
                style={{ width: 110 }}
                value={status}
                onChange={setStatus}
                options={[
                  { value: "success", label: "success" },
                  { value: "failed", label: "failed" },
                ]}
              />
              <Select
                style={{ width: 130 }}
                value={sort}
                onChange={setSort}
                options={[
                  { value: "newest", label: "最新优先" },
                  { value: "oldest", label: "最早优先" },
                  { value: "latency", label: "延迟最高" },
                  { value: "tokens", label: "Token 最高" },
                ]}
              />
            </Space>
          </Space>
          <Spin spinning={isLoading}>
            {filtered.length ? (
              <TraceTree
                traces={filtered}
                selectedId={selectedId}
                activeStep={activeStep}
                onSelect={select}
                onStepClick={(idx) => {
                  setActiveStep(idx);
                  setTab("steps");
                }}
              />
            ) : (
              <Empty description="暂无 Trace" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Spin>
        </Panel>

        <Panel
          title="Trace Detail"
          extra={
            active ? (
              <Space wrap>
                <Segmented
                  size="small"
                  value={tab}
                  onChange={(v) => setTab(v as DetailTab)}
                  options={[
                    {
                      value: "steps",
                      icon: <UnorderedListOutlined />,
                      label: "Steps",
                    },
                    { value: "dag", icon: <NodeIndexOutlined />, label: "DAG" },
                    {
                      value: "metrics",
                      icon: <BarChartOutlined />,
                      label: "Metrics",
                    },
                  ]}
                />
                <Tooltip title="复制 ID">
                  <Button size="small" icon={<CopyOutlined />} onClick={() => void copyId()} />
                </Tooltip>
                <Button
                  size="small"
                  icon={<BugOutlined />}
                  onClick={() => navigate(`/diagnosis?trace=${active.id}`)}
                >
                  诊断
                </Button>
                <Button
                  size="small"
                  type="primary"
                  ghost
                  icon={<ExperimentOutlined />}
                  loading={judgeMut.isPending}
                  onClick={onJudge}
                >
                  Judge
                </Button>
                <Tag color={active.status === "success" ? "success" : "error"}>
                  {active.status}
                </Tag>
              </Space>
            ) : null
          }
          bodyStyle={{ maxHeight: "calc(100vh - 200px)", overflow: "auto" }}
        >
          <Spin spinning={!!selectedId && detailLoading}>
            {!active ? (
              <Empty description="选择左侧 Trace 查看详情" />
            ) : (
              <>
                <RowMetrics active={active} />

                <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
                  <Descriptions.Item label="Trace ID" span={2}>
                    <span className="ic-mono">{active.id}</span>
                  </Descriptions.Item>
                  <Descriptions.Item label="Suite">
                    <span className="ic-mono">{shortId(active.test_suite_id, 12)}</span>
                  </Descriptions.Item>
                  <Descriptions.Item label="Created">
                    {formatDateTime(active.created_at)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Latency">
                    {active.response_time_ms} ms
                  </Descriptions.Item>
                  <Descriptions.Item label="Tokens">{active.total_tokens}</Descriptions.Item>
                  <Descriptions.Item label="Cost">
                    {active.cost != null ? `$${Number(active.cost).toFixed(6)}` : "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Model">
                    {active.model_version || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Agent">
                    {active.agent_version || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Prompt Ver">
                    {active.prompt_version || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tool Ver">
                    {active.tool_version || "—"}
                  </Descriptions.Item>
                  <Descriptions.Item label="Token Usage" span={2}>
                    prompt=
                    {active.token_usage?.prompt_tokens ?? active.prompt_tokens ?? "—"} ·
                    completion=
                    {active.token_usage?.completion_tokens ?? active.completion_tokens ?? "—"}
                  </Descriptions.Item>
                </Descriptions>

                <Divider orientation="left" plain>
                  Prompt / Input
                </Divider>
                <div className="ic-code">{active.user_query || "(empty)"}</div>

                {tab === "steps" ? (
                  <>
                    <Divider orientation="left" plain>
                      Steps ({active.steps?.length || 0})
                    </Divider>
                    {(active.steps || []).map((s, i) => (
                      <StepBlock
                        key={i}
                        step={s}
                        index={i}
                        highlighted={activeStep === i}
                        onClick={() => setActiveStep(i)}
                      />
                    ))}
                    {!active.steps?.length ? (
                      <Empty description="无步骤数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : null}
                  </>
                ) : null}

                {tab === "dag" ? (
                  <>
                    <Divider orientation="left" plain>
                      Execution DAG
                    </Divider>
                    {(active.steps || []).length ? (
                      <div
                        className="ic-panel"
                        style={{ padding: 8, minHeight: 420, marginBottom: 12 }}
                      >
                        <TraceFlowChart steps={active.steps || []} />
                      </div>
                    ) : (
                      <Empty description="无步骤，无法渲染 DAG" />
                    )}
                  </>
                ) : null}

                {tab === "metrics" ? (
                  <>
                    <Divider orientation="left" plain>
                      Metrics
                    </Divider>
                    <div style={{ marginBottom: 16 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        Step token curve
                      </Text>
                      <EChart option={stepTokenSeries} height={220} />
                    </div>
                    {(active.metric_scores || []).length ? (
                      <>
                        <EChart option={scoreBar} height={240} />
                        <Divider orientation="left" plain>
                          Score reasons
                        </Divider>
                        {active.metric_scores.map((ms) => (
                          <div key={ms.id} style={{ marginBottom: 12 }}>
                            <div
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                gap: 8,
                              }}
                            >
                              <Text strong>{ms.metric_name}</Text>
                              <Text style={{ color: "var(--ic-cyan)" }}>{ms.score}</Text>
                            </div>
                            <Progress
                              percent={Math.min(100, Math.round(ms.score))}
                              size="small"
                              showInfo={false}
                              strokeColor="#00D4FF"
                            />
                            <Paragraph type="secondary" style={{ marginBottom: 0, fontSize: 12 }}>
                              {ms.reason}
                            </Paragraph>
                          </div>
                        ))}
                      </>
                    ) : (
                      <Empty
                        description="暂无评分 — 可点击 Judge 触发"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                      />
                    )}
                  </>
                ) : null}
              </>
            )}
          </Spin>
        </Panel>
      </div>
    </div>
  );
}

function RowMetrics({ active }: { active: Trace }) {
  const avgScore =
    active.metric_scores?.length
      ? active.metric_scores.reduce((s, m) => s + m.score, 0) / active.metric_scores.length
      : null;
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 10,
        marginBottom: 14,
      }}
    >
      <MetricCard
        label="Latency"
        value={`${active.response_time_ms ?? 0}ms`}
        tone="warning"
        icon={<ClockCircleOutlined />}
      />
      <MetricCard
        label="Tokens"
        value={(active.total_tokens ?? 0).toLocaleString()}
        tone="purple"
        icon={<ThunderboltOutlined />}
      />
      <MetricCard
        label="Steps"
        value={active.steps?.length ?? 0}
        tone="cyan"
        icon={<NodeIndexOutlined />}
      />
      <MetricCard
        label="Avg Score"
        value={avgScore != null ? avgScore.toFixed(1) : "—"}
        tone="success"
      />
    </div>
  );
}

function StepBlock({
  step,
  index,
  highlighted,
  onClick,
}: {
  step: TraceStep;
  index: number;
  highlighted?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        marginBottom: 12,
        borderRadius: 10,
        border: highlighted
          ? "1px solid var(--af-border-strong)"
          : "1px solid transparent",
        background: highlighted ? "var(--af-primary-soft)" : "transparent",
        padding: highlighted ? 8 : 0,
        cursor: "pointer",
      }}
    >
      <Space style={{ marginBottom: 6 }} wrap>
        <Tag color="blue">{stepLabel(step, index)}</Tag>
        <Tag>{stepKind(step)}</Tag>
        {step.tokens ? <Tag>{step.tokens} tok</Tag> : null}
        {step.iteration != null ? <Tag>iter {step.iteration}</Tag> : null}
      </Space>
      <div className="ic-code" style={{ maxHeight: 160 }}>
        {stepBody(step)}
      </div>
    </div>
  );
}

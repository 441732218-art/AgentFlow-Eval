/* Evaluation Analytics Center — radar · models · cost · heatmap from real series */

import { useMemo, useState } from "react";
import { Row, Col, Tag, Empty, Segmented, Space, Button, Spin } from "antd";
import {
  RadarChartOutlined,
  FundOutlined,
  DollarOutlined,
  ReloadOutlined,
  FieldTimeOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useBusinessKpis, useDashboardOverview, useTasks, useTraces } from "@/hooks";
import { Panel } from "@/components/widgets/Panel";
import { MetricCard } from "@/components/widgets/MetricCard";
import {
  EChart,
  buildRadarOption,
  buildHeatmapOption,
  buildLineOption,
  buildBarOption,
  buildDualAxisLineOption,
  buildDonutOption,
  CHART_COLORS,
} from "@/components/charts/EChart";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { mapMetricToDimension } from "@/lib/observability";

type WindowDays = 7 | 14 | 30;

const RADAR_DIMS = [
  "Reasoning",
  "Accuracy",
  "Tool Usage",
  "Speed",
  "Cost",
  "Safety",
] as const;

export default function AnalyticsPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<WindowDays>(14);
  const {
    data: overview,
    isLoading,
    isFetching,
    refetch,
  } = useDashboardOverview(days);
  const { data: kpiResp } = useBusinessKpis(days);
  const { data: tasks } = useTasks({ page: 1, page_size: 50 });
  const { data: traces } = useTraces({ page: 1, page_size: 80 });

  const kpis = kpiResp?.kpis;
  const success = kpis?.success_rate ?? overview?.success_rate ?? null;
  const avgScore = kpis?.avg_metric_score ?? overview?.avg_score ?? null;
  const totalTokens = kpis?.total_tokens ?? overview?.tokens ?? 0;
  const latencyMs = kpis?.avg_trace_latency_ms ?? overview?.latency_ms ?? null;
  const failure = overview?.failure_rate ?? null;

  /** Build radar from metric_scores when present; fallback to KPI-derived dims */
  const radarValues = useMemo(() => {
    const acc: Record<string, { sum: number; n: number }> = {};
    for (const dim of RADAR_DIMS) acc[dim] = { sum: 0, n: 0 };

    for (const tr of traces?.items || []) {
      for (const ms of tr.metric_scores || []) {
        const dim = mapMetricToDimension(ms.metric_name) || "Accuracy";
        if (!acc[dim]) acc[dim] = { sum: 0, n: 0 };
        acc[dim].sum += ms.score;
        acc[dim].n += 1;
      }
    }

    const hasScores = Object.values(acc).some((v) => v.n > 0);
    if (hasScores) {
      return RADAR_DIMS.map((d) =>
        acc[d].n ? Math.round(acc[d].sum / acc[d].n) : 50
      );
    }

    // KPI-derived fallback (no synthetic floors for empty fleet)
    const sr = success != null ? success * 100 : 0;
    const sc = avgScore != null ? avgScore : 0;
    const speed =
      latencyMs != null
        ? Math.max(0, Math.min(100, 100 - Math.min(100, latencyMs / 80)))
        : 50;
    const cost =
      totalTokens > 0
        ? Math.max(10, 100 - Math.min(90, totalTokens / 5000))
        : 50;
    const tool = Math.min(
      100,
      ((overview?.stats?.suites_total ?? 0) / Math.max(overview?.stats?.tasks_total || 1, 1)) *
        40 +
        40
    );
    const safety = failure != null ? Math.max(0, (1 - failure) * 100) : 50;
    return [
      Math.round(sc || sr * 0.9),
      Math.round(sc || sr),
      Math.round(tool),
      Math.round(speed),
      Math.round(cost),
      Math.round(safety),
    ];
  }, [traces, success, avgScore, latencyMs, totalTokens, overview, failure]);

  const radar = useMemo(
    () =>
      buildRadarOption(
        RADAR_DIMS.map((name) => ({ name, max: 100 })),
        radarValues,
        "Fleet"
      ),
    [radarValues]
  );

  const modelCompare = useMemo(() => {
    const buckets: Record<string, { n: number; done: number; tokens: number }> = {};
    for (const t of tasks?.items || []) {
      const model = String(
        (t.agent_config as { model?: string })?.model || "unknown"
      );
      let key = "Other";
      const m = model.toLowerCase();
      if (m.includes("gpt") || m.includes("o1") || m.includes("o3")) key = "GPT";
      else if (m.includes("claude")) key = "Claude";
      else if (m.includes("local") || m.includes("ollama") || m.includes("llama"))
        key = "Local";
      else if (m !== "unknown") key = model.slice(0, 18);
      if (!buckets[key]) buckets[key] = { n: 0, done: 0, tokens: 0 };
      buckets[key].n += 1;
      if (t.status === "completed") buckets[key].done += 1;
    }
    // Enrich tokens from traces by model_version
    for (const tr of traces?.items || []) {
      const mv = (tr.model_version || "").toLowerCase();
      let key = "Other";
      if (mv.includes("gpt") || mv.includes("o1")) key = "GPT";
      else if (mv.includes("claude")) key = "Claude";
      else if (mv.includes("llama") || mv.includes("local")) key = "Local";
      if (!buckets[key]) buckets[key] = { n: 0, done: 0, tokens: 0 };
      buckets[key].tokens += tr.total_tokens || 0;
    }

    const entries = Object.entries(buckets);
    if (!entries.length) {
      return buildBarOption([]);
    }
    return buildBarOption(
      entries.map(([name, v]) => ({ name, value: v.n })),
      {
        colors: [
          CHART_COLORS.cyan,
          CHART_COLORS.purple,
          CHART_COLORS.success,
          CHART_COLORS.warning,
        ],
      }
    );
  }, [tasks, traces]);

  const modelDoneOption = useMemo(() => {
    const buckets: Record<string, number> = {};
    for (const t of tasks?.items || []) {
      const model = String(
        (t.agent_config as { model?: string })?.model || "unknown"
      ).toLowerCase();
      let key = "Other";
      if (model.includes("gpt") || model.includes("o1")) key = "GPT";
      else if (model.includes("claude")) key = "Claude";
      else if (model.includes("local") || model.includes("llama")) key = "Local";
      buckets[key] = (buckets[key] || 0) + (t.status === "completed" ? 1 : 0);
    }
    return buildDonutOption(
      Object.entries(buckets).map(([name, value]) => ({ name, value })),
      { title: "done" }
    );
  }, [tasks]);

  /** Heatmap from real daily series (not synthetic weekdays) */
  const heatmap = useMemo(() => {
    const s = overview?.series;
    if (!s?.tokens?.length) {
      return buildHeatmapOption([], [], []);
    }
    const xLabels = s.tokens.map((p) => p.t);
    const yLabels = ["Tasks", "Tokens", "Latency", "Errors", "Success%"];
    const rows = [s.agents, s.tokens, s.latency, s.errors, s.success_rate || []];
    // Normalize each row to 0-100 for visual comparability
    const data: Array<[number, number, number]> = [];
    rows.forEach((row, y) => {
      const vals = row.map((p) => p.v);
      const max = Math.max(1, ...vals);
      vals.forEach((v, x) => {
        data.push([x, y, Math.round((v / max) * 100)]);
      });
    });
    return buildHeatmapOption(xLabels, yLabels, data);
  }, [overview]);

  const costDual = useMemo(() => {
    const s = overview?.series;
    if (!s) {
      return buildDualAxisLineOption(
        { name: "Tokens", data: [] },
        { name: "Errors", data: [] }
      );
    }
    return buildDualAxisLineOption(
      { name: "Tokens", data: s.tokens, color: CHART_COLORS.purple },
      { name: "Errors", data: s.errors, color: CHART_COLORS.danger }
    );
  }, [overview]);

  const latencySuccess = useMemo(() => {
    const s = overview?.series;
    if (!s) return buildLineOption([]);
    return buildLineOption(
      [
        {
          name: "Latency ms",
          data: s.latency,
          color: CHART_COLORS.warning,
        },
        {
          name: "Success %",
          data: s.success_rate || [],
          color: CHART_COLORS.success,
        },
      ],
      { area: true }
    );
  }, [overview]);

  const scoreHist = useMemo(() => {
    const scores: number[] = [];
    for (const tr of traces?.items || []) {
      for (const ms of tr.metric_scores || []) scores.push(ms.score);
    }
    if (!scores.length) return buildBarOption([]);
    // Bucket 0-20, 20-40, ...
    const buckets = [0, 0, 0, 0, 0];
    for (const s of scores) {
      const i = Math.min(4, Math.floor(s / 20));
      buckets[i] += 1;
    }
    return buildBarOption(
      buckets.map((value, i) => ({
        name: `${i * 20}-${i * 20 + 20}`,
        value,
      }))
    );
  }, [traces]);

  if (isLoading && !overview) return <PageSkeleton variant="dashboard" />;

  const hasTasks = (tasks?.items?.length ?? 0) > 0;

  return (
    <div className="ic-page">
      <div className="ic-page-header">
        <div className="ic-page-header__main">
          <div className="ic-page-header__icon">
            <RadarChartOutlined />
          </div>
          <div>
            <div className="ic-page-header__title-row">
              <h1 className="af-section-title" style={{ margin: 0 }}>
                Evaluation Analytics
              </h1>
              <span className="ic-live-badge">
                <span className="af-live-dot" /> {days}d
              </span>
            </div>
            <p className="af-section-sub" style={{ margin: "4px 0 0" }}>
              能力雷达 · 模型对比 · 成本与真实日级热力（ORM series）
            </p>
          </div>
        </div>
        <div className="ic-page-header__extra">
          <Space wrap>
            <Segmented
              value={days}
              onChange={(v) => setDays(Number(v) as WindowDays)}
              options={[
                { label: "7d", value: 7 },
                { label: "14d", value: 14 },
                { label: "30d", value: 30 },
              ]}
            />
            <Button
              icon={<ReloadOutlined spin={isFetching} />}
              onClick={() => void refetch()}
            />
            <Button onClick={() => navigate("/dashboard")}>Dashboard</Button>
            <Button onClick={() => navigate("/traces")}>Traces</Button>
          </Space>
        </div>
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 14 }}>
        <Col xs={12} md={6}>
          <MetricCard
            label="Success"
            value={success != null ? `${Math.round(success * 100)}%` : "—"}
            tone="success"
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="Avg Score"
            value={avgScore != null ? Number(avgScore).toFixed(1) : "—"}
            tone="cyan"
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label={`Tokens (${days}d)`}
            value={totalTokens.toLocaleString()}
            tone="purple"
            icon={<DollarOutlined />}
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="Avg Latency"
            value={latencyMs != null ? `${Math.round(latencyMs)}ms` : "—"}
            tone="warning"
            icon={<FieldTimeOutlined />}
          />
        </Col>
      </Row>

      <Spin spinning={isFetching && !isLoading}>
        <Row gutter={[14, 14]}>
          <Col xs={24} lg={10}>
            <Panel
              title={
                <>
                  <RadarChartOutlined /> Agent Capability Radar
                </>
              }
              extra={
                <Tag color="cyan">
                  {(traces?.items || []).some((t) => t.metric_scores?.length)
                    ? "from scores"
                    : "from KPIs"}
                </Tag>
              }
            >
              <EChart option={radar} height={320} />
            </Panel>
          </Col>
          <Col xs={24} lg={14}>
            <Panel
              title={
                <>
                  <FundOutlined /> Model Compare
                </>
              }
              extra={<Tag>task.agent_config.model</Tag>}
            >
              {!hasTasks ? (
                <Empty description="暂无任务 — 创建评测后展示模型分布" />
              ) : (
                <Row gutter={12}>
                  <Col span={14}>
                    <EChart option={modelCompare} height={280} />
                  </Col>
                  <Col span={10}>
                    <EChart option={modelDoneOption} height={280} />
                  </Col>
                </Row>
              )}
            </Panel>
          </Col>
          <Col xs={24} lg={12}>
            <Panel
              title="Ops Heatmap · Daily × Metrics"
              extra={<Tag>normalized 0–100</Tag>}
            >
              {(overview?.series?.tokens?.length ?? 0) === 0 ? (
                <Empty description="暂无时序数据" />
              ) : (
                <EChart option={heatmap} height={300} />
              )}
            </Panel>
          </Col>
          <Col xs={24} lg={12}>
            <Panel
              title={
                <>
                  <DollarOutlined /> Cost · Tokens × Errors
                </>
              }
              extra={<Tag>dual-axis</Tag>}
            >
              <EChart option={costDual} height={300} />
            </Panel>
          </Col>
          <Col xs={24} lg={12}>
            <Panel
              title={
                <>
                  <ThunderboltOutlined /> Latency × Success
                </>
              }
            >
              <EChart option={latencySuccess} height={280} />
            </Panel>
          </Col>
          <Col xs={24} lg={12}>
            <Panel title="Score Distribution" extra={<Tag>metric_scores</Tag>}>
              {(traces?.items || []).every((t) => !t.metric_scores?.length) ? (
                <Empty description="暂无评分分布 — 执行 Judge 后可见" />
              ) : (
                <EChart option={scoreHist} height={280} />
              )}
            </Panel>
          </Col>
        </Row>
      </Spin>
    </div>
  );
}

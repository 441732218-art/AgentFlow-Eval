/* Intelligence Center — AI Command Cockpit (ECharts + ReactFlow) */

import { useMemo, useState } from "react";
import {
  Row,
  Col,
  Button,
  Space,
  Alert,
  Tag,
  Spin,
  Segmented,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  ThunderboltOutlined,
  FieldTimeOutlined,
  FireOutlined,
  DashboardOutlined,
  ApiOutlined,
  ReloadOutlined,
  ApartmentOutlined,
  PieChartOutlined,
  BugOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useDashboardOverview } from "@/hooks";
import { MetricCard } from "@/components/widgets/MetricCard";
import { Panel } from "@/components/widgets/Panel";
import { AgentTopologyFlow } from "@/components/flow/AgentTopologyFlow";
import {
  EChart,
  buildLineOption,
  buildDualAxisLineOption,
  buildGaugeOption,
  buildDonutOption,
  buildBarOption,
  CHART_COLORS,
} from "@/components/charts/EChart";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { QuotaStrip } from "@/components/billing/QuotaStrip";
import type { TopologyNodeMeta } from "@/components/flow/AgentTopologyFlow";

function pct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

type WindowDays = 7 | 14 | 30;

export default function DashboardPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<WindowDays>(7);
  const { data, isLoading, error, refetch, isFetching } = useDashboardOverview(days);

  const gaugeOption = useMemo(
    () => buildGaugeOption(data?.health ?? 0, "AI Health"),
    [data?.health]
  );

  const dualTrendOption = useMemo(() => {
    if (!data?.series) {
      return buildDualAxisLineOption(
        { name: "Tokens", data: [] },
        { name: "Latency ms", data: [] }
      );
    }
    return buildDualAxisLineOption(
      {
        name: "Tokens",
        data: data.series.tokens,
        color: CHART_COLORS.purple,
      },
      {
        name: "Latency ms",
        data: data.series.latency,
        color: CHART_COLORS.warning,
      }
    );
  }, [data]);

  const agentsErrorsOption = useMemo(() => {
    if (!data?.series) return buildLineOption([]);
    return buildLineOption(
      [
        {
          name: "Tasks / day",
          data: data.series.agents,
          color: CHART_COLORS.cyan,
        },
        {
          name: "Errors",
          data: data.series.errors,
          color: CHART_COLORS.danger,
        },
        ...(data.series.success_rate?.length
          ? [
              {
                name: "Success %",
                data: data.series.success_rate,
                color: CHART_COLORS.success,
              },
            ]
          : []),
      ],
      { area: true }
    );
  }, [data]);

  const statusDonut = useMemo(() => {
    const items = data?.status_distribution?.length
      ? data.status_distribution
      : Object.entries(data?.stats?.tasks_by_status || {}).map(([name, value]) => ({
          name,
          value: Number(value),
        }));
    return buildDonutOption(items.filter((i) => i.value > 0), { title: "tasks" });
  }, [data]);

  const errorBar = useMemo(() => {
    const items = data?.error_topology?.length
      ? data.error_topology
      : [
          { name: "failed", value: data?.stats?.failed_tasks ?? 0 },
          { name: "running", value: data?.agents ?? 0 },
        ];
    return buildBarOption(items, { horizontal: true });
  }, [data]);

  if (isLoading && !data) {
    return <PageSkeleton variant="dashboard" />;
  }

  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message="驾驶舱加载失败"
        description={(error as Error).message}
        action={
          <Button size="small" onClick={() => void refetch()}>
            重试
          </Button>
        }
      />
    );
  }

  const success = data?.success_rate;
  const failure = data?.failure_rate;
  const latencySec = data?.latency;
  const seriesSource = data?.series_meta?.source || "orm";

  return (
    <div className="ic-page">
      <div className="ic-page-header">
        <div className="ic-page-header__main">
          <div className="ic-page-header__icon">
            <DashboardOutlined />
          </div>
          <div className="ic-page-header__text">
            <div className="ic-page-header__title-row">
              <h1 className="af-section-title" style={{ margin: 0 }}>
                AI Command Center
              </h1>
              <span className="ic-live-badge">
                <span className="af-live-dot" /> Live
              </span>
            </div>
            <p className="af-section-sub" style={{ margin: "4px 0 0" }}>
              ECharts 时序 · ReactFlow 拓扑 · 可观测评测驾驶舱
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
            <Tooltip title="刷新 overview">
              <Button
                icon={<ReloadOutlined spin={isFetching} />}
                onClick={() => void refetch()}
              />
            </Tooltip>
            <Button icon={<ApiOutlined />} onClick={() => navigate("/monitoring")}>
              Monitoring
            </Button>
            <Button icon={<BugOutlined />} onClick={() => navigate("/diagnosis")}>
              Diagnosis
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate("/tasks/create")}
              className="ic-btn-gradient"
            >
              创建任务
            </Button>
          </Space>
        </div>
      </div>

      <QuotaStrip />

      <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="AI Health"
            value={data ? `${data.health.toFixed(1)}%` : "—"}
            tone="cyan"
            hint="成功率 / 延迟 / 故障压力"
            icon={<DashboardOutlined />}
          />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="Running Agents"
            value={data?.agents ?? 0}
            tone="purple"
            hint="排队 + 运行 + 评分中"
            icon={<ThunderboltOutlined />}
            onClick={() => navigate("/tasks?status=running")}
          />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="Success Rate"
            value={pct(success)}
            tone="success"
            hint={`${days}d 终态成功率`}
          />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="Failure Rate"
            value={pct(failure)}
            tone="danger"
            hint="failed + timeout"
            icon={<FireOutlined />}
            onClick={() => navigate("/tasks?status=failed")}
          />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="Avg Latency"
            value={latencySec != null ? `${latencySec.toFixed(2)}s` : "—"}
            tone="warning"
            hint={
              data?.latency_ms != null
                ? `${Math.round(data.latency_ms)} ms`
                : "trace avg"
            }
            icon={<FieldTimeOutlined />}
          />
        </Col>
        <Col xs={12} sm={8} lg={4}>
          <MetricCard
            label="Token Cost"
            value={(data?.tokens ?? 0).toLocaleString()}
            tone="cyan"
            hint={data?.cost != null ? `$${data.cost}` : `${days}d Token 总量`}
          />
        </Col>
      </Row>

      <Row gutter={[14, 14]} style={{ marginBottom: 14 }}>
        <Col xs={24} lg={8}>
          <Panel
            title={
              <>
                <DashboardOutlined /> Health Gauge
              </>
            }
            extra={<Tag color="cyan">{days}d</Tag>}
          >
            <Spin spinning={isFetching && !isLoading}>
              <EChart option={gaugeOption} height={280} />
            </Spin>
          </Panel>
        </Col>
        <Col xs={24} lg={16}>
          <Panel
            title={
              <>
                <ThunderboltOutlined /> Tokens × Latency
              </>
            }
            extra={
              <Tag>
                dual-axis · {seriesSource}
              </Tag>
            }
          >
            <Spin spinning={isFetching && !isLoading}>
              <EChart option={dualTrendOption} height={280} />
            </Spin>
          </Panel>
        </Col>
      </Row>

      <Row gutter={[14, 14]} style={{ marginBottom: 14 }}>
        <Col xs={24}>
          <Panel
            title={
              <>
                <ApartmentOutlined /> Agent Pipeline Topology
              </>
            }
            extra={
              <Space size={6}>
                <Tag className="ic-live-badge" style={{ border: "none" }}>
                  ReactFlow
                </Tag>
                <Tag>{data?.topology?.layout || "horizontal"}</Tag>
              </Space>
            }
          >
            <AgentTopologyFlow
              layout={data?.topology?.layout === "vertical" ? "vertical" : "horizontal"}
              legend={data?.topology?.legend}
              nodes={(data?.topology?.nodes || []).map((n) => ({
                id: n.id,
                label: n.label,
                status: n.status,
                kind: n.kind,
                meta: n.meta as TopologyNodeMeta,
              }))}
              edges={data?.topology?.edges || []}
              height={320}
              showMiniMap
            />
          </Panel>
        </Col>
      </Row>

      <Row gutter={[14, 14]}>
        <Col xs={24} lg={10}>
          <Panel
            title={
              <>
                <PieChartOutlined /> Status Distribution
              </>
            }
            extra={<Tag>fleet</Tag>}
          >
            <Spin spinning={isFetching && !isLoading}>
              <EChart option={statusDonut} height={280} />
            </Spin>
          </Panel>
        </Col>
        <Col xs={24} lg={14}>
          <Panel
            title={
              <>
                <FireOutlined /> Tasks / Errors / Success
              </>
            }
            extra={<Button type="link" size="small" onClick={() => navigate("/analytics")}>Analytics</Button>}
          >
            <Spin spinning={isFetching && !isLoading}>
              <EChart option={agentsErrorsOption} height={280} />
            </Spin>
          </Panel>
        </Col>
        <Col xs={24} lg={10}>
          <Panel title="Error Topology" extra={<Tag color="red">stages</Tag>}>
            <Spin spinning={isFetching && !isLoading}>
              <EChart option={errorBar} height={260} />
            </Spin>
          </Panel>
        </Col>
        <Col xs={24} lg={14}>
          <Panel title="Fleet Snapshot" extra={<Tag>stats</Tag>}>
            <Row gutter={[12, 12]}>
              <Col xs={12} sm={6}>
                <MetricCard
                  label="Tasks Total"
                  value={data?.stats?.tasks_total ?? 0}
                  tone="cyan"
                  onClick={() => navigate("/tasks")}
                />
              </Col>
              <Col xs={12} sm={6}>
                <MetricCard
                  label="Completed"
                  value={data?.stats?.completed_tasks ?? 0}
                  tone="success"
                />
              </Col>
              <Col xs={12} sm={6}>
                <MetricCard
                  label="Failed"
                  value={data?.stats?.failed_tasks ?? 0}
                  tone="danger"
                  onClick={() => navigate("/diagnosis")}
                />
              </Col>
              <Col xs={12} sm={6}>
                <MetricCard
                  label="Suites"
                  value={data?.stats?.suites_total ?? 0}
                  tone="purple"
                />
              </Col>
              <Col span={24}>
                <div className="ic-toolbar" style={{ marginBottom: 0 }}>
                  <Tag color="cyan">avg score {data?.avg_score?.toFixed?.(2) ?? "—"}</Tag>
                  <Tag>window {data?.window_days ?? days}d</Tag>
                  <Tag>series {seriesSource}</Tag>
                  <Button size="small" type="link" onClick={() => navigate("/traces")}>
                    Trace Explorer →
                  </Button>
                </div>
              </Col>
            </Row>
          </Panel>
        </Col>
      </Row>
    </div>
  );
}

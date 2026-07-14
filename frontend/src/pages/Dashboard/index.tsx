/* (c) 2026 AgentFlow-Eval */
/* Dashboard — stats + drill-down */

import React, { useMemo } from "react";
import {
  Card,
  Col,
  Row,
  Tag,
  Button,
  Alert,
  Typography,
  Space,
  Progress,
  Empty,
  Tooltip,
} from "antd";
import {
  ExperimentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  PlusOutlined,
  ArrowRightOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { useTasks } from "@/hooks";
import { formatDateTime } from "@/utils/format";
import type { Task } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge, OwnerBadge } from "@/components/ui/StatusBadge";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { useI18nStore } from "@/i18n";

const { Text } = Typography;

const PIE_COLORS = ["#38bdf8", "#818cf8", "#34d399", "#f87171", "#fbbf24", "#94a3b8"];

const FILTER_PREF_KEY = "agentflow_dashboard_filter";

function goTasks(navigate: ReturnType<typeof useNavigate>, status?: string) {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  try {
    localStorage.setItem(
      FILTER_PREF_KEY,
      JSON.stringify({ status: status || "", at: Date.now() })
    );
  } catch {
    /* ignore */
  }
  navigate(status ? `/tasks?status=${encodeURIComponent(status)}` : "/tasks");
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const t = useI18nStore((s) => s.t);
  const { data, isLoading, error, refetch } = useTasks({ page: 1, page_size: 50 });

  const tasks = data?.items ?? [];
  const total = data?.total ?? 0;

  const stats = useMemo(() => {
    const running = tasks.filter((t) =>
      ["running", "queued", "judging", "waiting_tool"].includes(t.status)
    ).length;
    const completed = tasks.filter((t) => t.status === "completed").length;
    const failed = tasks.filter((t) => ["failed", "timeout"].includes(t.status)).length;
    const created = tasks.filter((t) => t.status === "created").length;
    return { total, running, completed, failed, created };
  }, [tasks, total]);

  const pieData = useMemo(() => {
    const map: Record<string, number> = {};
    tasks.forEach((t) => {
      map[t.status] = (map[t.status] || 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  }, [tasks]);

  const barData = useMemo(() => {
    // Last 7 buckets by day label of created_at
    const buckets: Record<string, number> = {};
    tasks.forEach((t) => {
      if (!t.created_at) return;
      const d = new Date(t.created_at);
      const key = `${d.getMonth() + 1}/${d.getDate()}`;
      buckets[key] = (buckets[key] || 0) + 1;
    });
    return Object.entries(buckets)
      .slice(-7)
      .map(([day, count]) => ({ day, count }));
  }, [tasks]);

  const completionRate =
    stats.total > 0 ? Math.round((stats.completed / Math.max(stats.total, 1)) * 100) : 0;

  if (isLoading) {
    return <PageSkeleton variant="dashboard" />;
  }

  if (error) {
    const errMsg = (error as Error)?.message || "未知错误";
    return (
      <Alert
        type="error"
        message="加载总览失败"
        description={
          <div>
            <div>{errMsg}</div>
            <div style={{ marginTop: 8, opacity: 0.75, fontSize: 12 }}>
              本地开发请先启动后端（端口 8000），再刷新本页。可运行 scripts/start-local.ps1
            </div>
          </div>
        }
        showIcon
        action={
          <Button size="small" onClick={() => refetch()}>
            重试
          </Button>
        }
      />
    );
  }

  const statCards = [
    {
      title: t("dashboard.total"),
      value: stats.total,
      icon: <ExperimentOutlined />,
      color: "var(--af-primary)",
      status: "",
    },
    {
      title: t("dashboard.running"),
      value: stats.running,
      icon: <ClockCircleOutlined />,
      color: "#818cf8",
      status: "running",
    },
    {
      title: t("dashboard.completed"),
      value: stats.completed,
      icon: <CheckCircleOutlined />,
      color: "var(--af-success)",
      status: "completed",
    },
    {
      title: t("dashboard.failed"),
      value: stats.failed,
      icon: <CloseCircleOutlined />,
      color: "var(--af-danger)",
      status: "failed",
    },
  ];

  return (
    <div className="af-page">
      <PageHeader
        title={t("dashboard.title")}
        subtitle={t("dashboard.subtitle")}
        icon={<DashboardOutlined />}
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/tasks/create")}
            style={{ background: "var(--af-gradient)", border: "none" }}
          >
            {t("dashboard.create")}
          </Button>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        {statCards.map((s) => (
          <Col xs={12} lg={6} key={s.title}>
            <Tooltip title={t("dashboard.clickHint")}>
              <Card
                className="af-glass af-card-hover"
                styles={{ body: { padding: 18 } }}
                style={{ cursor: "pointer" }}
                onClick={() => goTasks(navigate, s.status || undefined)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {s.title}
                    </Text>
                    <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.03em", marginTop: 4 }}>
                      {s.value}
                    </div>
                  </div>
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 12,
                      background: "var(--af-bg-muted)",
                      display: "grid",
                      placeItems: "center",
                      color: s.color,
                      fontSize: 18,
                    }}
                  >
                    {s.icon}
                  </div>
                </div>
              </Card>
            </Tooltip>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={8}>
          <Card
            className="af-glass af-card-hover"
            title={t("dashboard.rate")}
            styles={{ body: { padding: 20, textAlign: "center" } }}
            style={{ cursor: "pointer" }}
            onClick={() => goTasks(navigate, "completed")}
          >
            <Progress
              type="dashboard"
              percent={completionRate}
              strokeColor={{ "0%": "#38bdf8", "100%": "#818cf8" }}
              size={140}
            />
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">
                {stats.completed} / {stats.total} {t("dashboard.completed")}
              </Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card className="af-glass" title={t("dashboard.statusDist")} styles={{ body: { height: 220 } }}>
            {pieData.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t("dashboard.noData")} />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={3}
                    style={{ cursor: "pointer" }}
                    onClick={(_, index) => {
                      const slice = pieData[index];
                      if (slice?.name) goTasks(navigate, slice.name);
                    }}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <RTooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card className="af-glass" title={t("dashboard.trend")} styles={{ body: { height: 220 } }}>
            {barData.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t("dashboard.noData")} />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--af-border)" />
                  <XAxis dataKey="day" tick={{ fill: "var(--af-text-muted)", fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fill: "var(--af-text-muted)", fontSize: 11 }} />
                  <RTooltip />
                  <Bar
                    dataKey="count"
                    fill="#38bdf8"
                    radius={[6, 6, 0, 0]}
                    cursor="pointer"
                    onClick={() => goTasks(navigate)}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

      <Card
        className="af-glass"
        title={
          <Space>
            <span>{t("dashboard.recent")}</span>
            <Tag>{Math.min(tasks.length, 8)}</Tag>
          </Space>
        }
        extra={
          <Button type="link" onClick={() => goTasks(navigate)} icon={<ArrowRightOutlined />}>
            {t("dashboard.allTasks")}
          </Button>
        }
      >
        {tasks.length === 0 ? (
          <Empty description={t("dashboard.noTasks")} />
        ) : (
          <Space direction="vertical" size={10} style={{ width: "100%" }}>
            {tasks.slice(0, 8).map((t: Task) => (
              <div
                key={t.id}
                onClick={() => navigate(`/tasks/${t.id}`)}
                className="af-card-hover"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "1px solid var(--af-border)",
                  background: "var(--af-bg-muted)",
                  cursor: "pointer",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <Text strong ellipsis style={{ display: "block" }}>
                    {t.name}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatDateTime(t.created_at)} · {t.test_suite_count} 用例
                  </Text>
                </div>
                <Space>
                  <OwnerBadge owner={t.created_by} />
                  <StatusBadge status={t.status} />
                </Space>
              </div>
            ))}
          </Space>
        )}
      </Card>
    </div>
  );
};

export default Dashboard;

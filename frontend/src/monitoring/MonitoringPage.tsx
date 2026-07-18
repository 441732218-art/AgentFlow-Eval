/* Real-time Monitoring — K8s-style control plane */

import { useEffect, useMemo, useRef, useState } from "react";
import { Row, Col, Tag, Badge, Button, Space } from "antd";
import {
  CloudServerOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ClusterOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import {
  useDashboardOverview,
  useSlowTasks,
  useBusinessKpis,
  useLogs,
  useLogStatistics,
} from "@/hooks";
import { Panel } from "@/components/widgets/Panel";
import { MetricCard } from "@/components/widgets/MetricCard";
import { EChart, buildLineOption, CHART_COLORS } from "@/components/charts/EChart";
import { apiClient } from "@/api/client";

type HealthBody = {
  status?: string;
  redis?: { ok?: boolean; skipped?: boolean };
  database?: { ok?: boolean };
  checks?: Record<string, unknown>;
};

type LogLine = { ts: string; level: "info" | "warn" | "error"; msg: string };

export default function MonitoringPage() {
  const { data: overview, refetch: refetchOverview } = useDashboardOverview(7);
  const { data: slow } = useSlowTasks(12, "auto");
  const { data: kpis } = useBusinessKpis(1);
  const { data: aolsLogs, refetch: refetchLogs } = useLogs({
    page: 1,
    page_size: 40,
  });
  const { data: logStats } = useLogStatistics(7);
  const [health, setHealth] = useState<HealthBody | null>(null);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const logEnd = useRef<HTMLDivElement>(null);

  const pushLog = (level: LogLine["level"], msg: string) => {
    const ts = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev.slice(-200), { ts, level, msg }]);
  };

  // Merge AOLS backend logs into stream
  useEffect(() => {
    const items = aolsLogs?.items || [];
    if (!items.length) return;
    const mapped: LogLine[] = items
      .slice()
      .reverse()
      .map((row) => {
        const lvl =
          row.level === "error"
            ? "error"
            : row.level === "warning" || row.level === "warn"
              ? "warn"
              : "info";
        const ts = row.created_at
          ? new Date(row.created_at).toLocaleTimeString()
          : new Date().toLocaleTimeString();
        return {
          ts,
          level: lvl as LogLine["level"],
          msg: `${row.event} svc=${row.service}${
            row.task_id ? ` task=${row.task_id.slice(0, 8)}` : ""
          }${row.trace_id ? ` trace=${row.trace_id.slice(0, 8)}` : ""}`,
        };
      });
    // Prefer backend stream when available
    setLogs(mapped.slice(-200));
  }, [aolsLogs]);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        // /health is outside /api/v1 — derive origin from API base
        const apiBase = apiClient.defaults.baseURL || "/api/v1";
        let healthUrl = "/health";
        try {
          if (apiBase.startsWith("http")) {
            const u = new URL(apiBase);
            healthUrl = `${u.origin}/health`;
          }
        } catch {
          /* use relative */
        }
        const res = await fetch(healthUrl, { credentials: "include" });
        const body = (await res.json()) as HealthBody;
        if (!cancelled) {
          setHealth(body);
          pushLog(res.ok ? "info" : "error", `health → ${body.status || res.status}`);
        }
      } catch (e) {
        if (!cancelled) {
          setHealth({ status: "unreachable" });
          pushLog("warn", `health probe failed: ${(e as Error).message}`);
        }
      }
    };
    void poll();
    const id = window.setInterval(() => void poll(), 8000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  // Simulate activity stream from slow tasks / KPI refresh
  useEffect(() => {
    if (slow?.items?.length) {
      const latest = slow.items[0];
      pushLog(
        "warn",
        `slow-task stage=${latest.stage} duration=${latest.duration_sec.toFixed(1)}s thr=${latest.threshold_sec}s`
      );
    }
  }, [slow]);

  useEffect(() => {
    if (overview) {
      pushLog(
        "info",
        `fleet agents=${overview.agents} health=${overview.health}% tokens=${overview.tokens}`
      );
    }
  }, [overview?.agents, overview?.health, overview?.tokens]);

  useEffect(() => {
    logEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs.length]);

  const seriesOpt = useMemo(() => {
    if (!overview?.series) return buildLineOption([]);
    return buildLineOption([
      { name: "Agents", data: overview.series.agents, color: CHART_COLORS.cyan },
      { name: "Errors", data: overview.series.errors, color: CHART_COLORS.danger },
    ]);
  }, [overview]);

  const redisOk = health?.redis?.ok !== false || health?.redis?.skipped;
  const dbOk = health?.database?.ok !== false;
  const apiOk = health?.status === "ok" || health?.status === "ready" || health?.status === "healthy";

  return (
    <div className="ic-page">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1 className="af-section-title">Realtime Monitoring</h1>
          <p className="af-section-sub">控制面状态 · Worker / Queue / Redis / API · 日志流</p>
        </div>
        <Space>
          <span className="ic-live-badge">
            <span className="af-live-dot" /> STREAM
          </span>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => {
              void refetchOverview();
              void refetchLogs();
              pushLog("info", "manual refresh");
            }}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 14 }}>
        <Col xs={12} md={6}>
          <MetricCard
            label="AOLS Events (7d)"
            value={logStats?.total_events ?? aolsLogs?.total ?? 0}
            tone="purple"
            hint={
              logStats?.error_count != null
                ? `errors/warn ${logStats.error_count}`
                : "from agent_logs"
            }
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="Running Agents"
            value={overview?.agents ?? 0}
            tone="cyan"
            icon={<ClusterOutlined />}
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="API"
            value={apiOk ? "UP" : health?.status || "DOWN"}
            tone={apiOk ? "success" : "danger"}
            icon={<ApiOutlined />}
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="Redis"
            value={health?.redis?.skipped ? "SKIP" : redisOk ? "UP" : "DOWN"}
            tone={redisOk ? "success" : "danger"}
            icon={<CloudServerOutlined />}
          />
        </Col>
        <Col xs={12} md={6}>
          <MetricCard
            label="Database"
            value={dbOk ? "UP" : "DOWN"}
            tone={dbOk ? "success" : "danger"}
            icon={<DatabaseOutlined />}
          />
        </Col>
      </Row>

      <Row gutter={[14, 14]}>
        <Col xs={24} lg={10}>
          <Panel title="Control Plane">
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { name: "API Gateway", ok: apiOk, detail: health?.status || "unknown" },
                {
                  name: "Redis Broker",
                  ok: !!redisOk,
                  detail: health?.redis?.skipped ? "eager/lite skip" : "broker",
                },
                { name: "PostgreSQL/SQLite", ok: !!dbOk, detail: "orm session" },
                {
                  name: "Celery Workers",
                  ok: (overview?.agents ?? 0) >= 0,
                  detail: `active tasks ≈ ${overview?.agents ?? 0}`,
                },
                {
                  name: "Queue Depth",
                  ok: true,
                  detail: `running window tasks ${kpis?.kpis?.tasks_total ?? "—"}`,
                },
              ].map((row) => (
                <div
                  key={row.name}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid var(--af-border)",
                    background: "rgba(0,0,0,0.2)",
                  }}
                >
                  <Space>
                    <Badge status={row.ok ? "success" : "error"} />
                    <strong>{row.name}</strong>
                  </Space>
                  <Tag color={row.ok ? "success" : "error"}>{row.detail}</Tag>
                </div>
              ))}
            </div>
          </Panel>
        </Col>
        <Col xs={24} lg={14}>
          <Panel title="Fleet Activity">
            <EChart option={seriesOpt} height={260} />
          </Panel>
        </Col>
        <Col xs={24} lg={12}>
          <Panel
            title="Live Log Stream"
            extra={
              <Tag color="cyan">
                AOLS {aolsLogs?.total != null ? `· ${aolsLogs.total}` : "· poll"}
              </Tag>
            }
          >
            <div className="ic-log-stream">
              {logs.length === 0 ? (
                <div className="lvl-info">
                  waiting for events… (emit agent/llm/tool logs via evaluation)
                </div>
              ) : (
                logs.map((l, i) => (
                  <div key={i}>
                    <span className="ts">{l.ts}</span>
                    <span className={`lvl-${l.level}`}>[{l.level}]</span> {l.msg}
                  </div>
                ))
              )}
              <div ref={logEnd} />
            </div>
          </Panel>
        </Col>
        <Col xs={24} lg={12}>
          <Panel title="Slow Tasks" extra={<Tag>{slow?.total ?? 0}</Tag>}>
            <div className="ic-log-stream" style={{ maxHeight: 360 }}>
              {(slow?.items || []).length === 0 ? (
                <div className="lvl-info">no slow tasks above threshold</div>
              ) : (
                (slow?.items || []).map((s, i) => (
                  <div key={i}>
                    <span className="ts">
                      {s.at ? new Date(s.at * 1000).toLocaleTimeString() : "--:--:--"}
                    </span>
                    <span className="lvl-warn">[slow]</span> {s.stage}{" "}
                    {s.duration_sec.toFixed(2)}s / thr {s.threshold_sec}s{" "}
                    {s.ref_id ? `ref=${s.ref_id.slice(0, 8)}` : ""}
                  </div>
                ))
              )}
            </div>
          </Panel>
        </Col>
      </Row>
    </div>
  );
}

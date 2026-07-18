/* Failure Diagnosis Center — evidence · topology · drift · deep links */

import { useEffect, useMemo, useState } from "react";
import {
  Row,
  Col,
  Select,
  Tag,
  Alert,
  Empty,
  Spin,
  List,
  Typography,
  Progress,
  Space,
  Button,
  Segmented,
  Collapse,
} from "antd";
import {
  BugOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  ApartmentOutlined,
  ReloadOutlined,
  NodeIndexOutlined,
} from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  useDiagnosisList,
  useTaskDiagnosis,
  useTraceDiagnosis,
  useTasks,
} from "@/hooks";
import { Panel } from "@/components/widgets/Panel";
import { MetricCard } from "@/components/widgets/MetricCard";
import { AgentTopologyFlow } from "@/components/flow/AgentTopologyFlow";
import {
  EChart,
  buildDualAxisLineOption,
  buildGaugeOption,
  buildBarOption,
  CHART_COLORS,
} from "@/components/charts/EChart";
import {
  ISSUE_COLOR,
  ISSUE_LABEL,
  ISSUE_TONE,
  shortId,
} from "@/lib/observability";
import type { DiagnosisResult } from "@/api/endpoints/diagnosis";

const { Text, Paragraph } = Typography;

type FocusIssue = "all" | string;

export default function DiagnosisPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const taskFromUrl = params.get("task") || undefined;
  const traceFromUrl = params.get("trace") || undefined;
  const [taskId, setTaskId] = useState<string | undefined>(taskFromUrl);
  const [focus, setFocus] = useState<FocusIssue>("all");

  const { data: tasksData } = useTasks({
    page: 1,
    page_size: 50,
    include_archived: false,
  });
  const { data: list, isLoading: listLoading } = useDiagnosisList(20);
  const {
    data: taskDetail,
    isLoading: taskLoading,
    refetch: refetchTask,
  } = useTaskDiagnosis(taskId);
  const {
    data: traceDetail,
    isLoading: traceLoading,
    refetch: refetchTrace,
  } = useTraceDiagnosis(traceFromUrl);

  useEffect(() => {
    if (taskFromUrl) setTaskId(taskFromUrl);
  }, [taskFromUrl]);

  // Prefer task diagnosis; fall back to trace-scoped diagnosis
  const detail: DiagnosisResult | undefined = taskId ? taskDetail : traceDetail;
  const detailLoading = taskId ? taskLoading : !!traceFromUrl && traceLoading;

  const confGauge = useMemo(
    () => buildGaugeOption((detail?.confidence ?? 0) * 100, "Confidence"),
    [detail?.confidence]
  );

  const dualOption = useMemo(() => {
    const curve = detail?.token_curve || [];
    return buildDualAxisLineOption(
      {
        name: "Tokens",
        color: CHART_COLORS.warning,
        data: curve.map((c, i) => ({ t: `#${i + 1}`, v: c.tokens })),
      },
      {
        name: "Latency ms",
        color: CHART_COLORS.cyan,
        data: curve.map((c, i) => ({ t: `#${i + 1}`, v: c.latency_ms || 0 })),
      }
    );
  }, [detail]);

  const issueBar = useMemo(() => {
    const issues = detail?.issues || [];
    return buildBarOption(
      issues.map((i) => ({
        name: ISSUE_LABEL[i.issue] || i.issue,
        value: Math.round(i.confidence * 100),
      })),
      { horizontal: true }
    );
  }, [detail]);

  const issues = useMemo(() => {
    const raw = detail?.issues || (detail ? [detail] : []);
    if (focus === "all") return raw;
    return raw.filter((i) => i.issue === focus);
  }, [detail, focus]);

  const issueTabs = useMemo(() => {
    const raw = detail?.issues || [];
    const seen = new Set<string>();
    const tabs: Array<{ label: string; value: string }> = [
      { label: "All", value: "all" },
    ];
    for (const i of raw) {
      if (seen.has(i.issue)) continue;
      seen.add(i.issue);
      tabs.push({
        label: ISSUE_LABEL[i.issue] || i.issue,
        value: i.issue,
      });
    }
    return tabs;
  }, [detail]);

  const refetch = () => {
    if (taskId) void refetchTask();
    else if (traceFromUrl) void refetchTrace();
  };

  return (
    <div className="ic-page">
      <div className="ic-page-header">
        <div className="ic-page-header__main">
          <div className="ic-page-header__icon">
            <BugOutlined />
          </div>
          <div>
            <div className="ic-page-header__title-row">
              <h1 className="af-section-title" style={{ margin: 0 }}>
                Failure Diagnosis Center
              </h1>
              <span className="ic-live-badge">
                <span className="af-live-dot" /> AI
              </span>
            </div>
            <p className="af-section-sub" style={{ margin: "4px 0 0" }}>
              Loop / Tool / Token / Prompt Drift · 证据链 · 可操作建议
            </p>
          </div>
        </div>
        <div className="ic-page-header__extra">
          <Space wrap>
            <Select
              showSearch
              allowClear
              placeholder="选择任务诊断"
              style={{ minWidth: 260 }}
              value={taskId}
              optionFilterProp="label"
              onChange={(v) => {
                setTaskId(v);
                if (v) setParams({ task: v });
                else if (traceFromUrl) setParams({ trace: traceFromUrl });
                else setParams({});
              }}
              options={(tasksData?.items || []).map((t) => ({
                value: t.id,
                label: `${t.name} (${t.status})`,
              }))}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={refetch}
              disabled={!taskId && !traceFromUrl}
            >
              重新分析
            </Button>
            <Button
              icon={<ApartmentOutlined />}
              onClick={() => navigate("/traces")}
            >
              Traces
            </Button>
          </Space>
        </div>
      </div>

      {traceFromUrl && !taskId ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 14 }}
          message="Trace-scoped diagnosis"
          description={
            <span>
              当前基于 Trace <span className="ic-mono">{shortId(traceFromUrl, 12)}</span>{" "}
              分析。可再选择任务做聚合诊断。
            </span>
          }
        />
      ) : null}

      <Row gutter={[14, 14]}>
        <Col xs={24} lg={8}>
          <Panel
            title={
              <>
                <BugOutlined /> Recent Diagnoses
              </>
            }
            extra={<Tag>{list?.total ?? 0}</Tag>}
            bodyStyle={{ maxHeight: 640, overflow: "auto" }}
          >
            <Spin spinning={listLoading}>
              <List
                dataSource={list?.items || []}
                locale={{
                  emptyText: (
                    <Empty description="暂无诊断样本。请执行 python -m app.core.seed --force 或先跑失败评测" />
                  ),
                }}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: "pointer",
                      borderRadius: 8,
                      padding: "10px 8px",
                      background:
                        item.task_id === taskId
                          ? "var(--af-primary-soft)"
                          : "transparent",
                    }}
                    onClick={() => {
                      if (item.task_id) {
                        setTaskId(item.task_id);
                        setParams({ task: item.task_id });
                      }
                    }}
                  >
                    <List.Item.Meta
                      title={
                        <Space wrap>
                          <Text strong style={{ fontSize: 13 }}>
                            {item.task_name || shortId(item.task_id || "", 10)}
                          </Text>
                          <Tag color={ISSUE_COLOR[item.issue] || "default"}>
                            {ISSUE_LABEL[item.issue] || item.issue}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div style={{ fontSize: 12 }}>
                          <Progress
                            percent={Math.round(item.confidence * 100)}
                            size="small"
                            strokeColor="#00D4FF"
                            style={{ maxWidth: 160, marginBottom: 4 }}
                          />
                          <div style={{ color: "var(--af-text-muted)" }}>
                            {item.root_cause.slice(0, 100)}
                            {item.root_cause.length > 100 ? "…" : ""}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </Spin>
          </Panel>
        </Col>

        <Col xs={24} lg={16}>
          <Spin spinning={detailLoading}>
            {!taskId && !traceFromUrl ? (
              <Panel title="Diagnosis Detail">
                <Empty description="请选择任务，或从 Trace Explorer 带 ?trace= 进入" />
              </Panel>
            ) : !detail ? (
              <Panel title="Diagnosis Detail">
                <Empty description="无法加载诊断结果" />
              </Panel>
            ) : (
              <>
                <Row gutter={[12, 12]} style={{ marginBottom: 14 }}>
                  <Col xs={12} md={6}>
                    <MetricCard
                      label="Primary Issue"
                      value={ISSUE_LABEL[detail.issue] || detail.issue}
                      tone={ISSUE_TONE[detail.issue] || "danger"}
                      icon={<WarningOutlined />}
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <MetricCard
                      label="Confidence"
                      value={`${(detail.confidence * 100).toFixed(0)}%`}
                      tone="cyan"
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <MetricCard
                      label="Failed Traces"
                      value={detail.summary?.traces_failed ?? 0}
                      tone="danger"
                    />
                  </Col>
                  <Col xs={12} md={6}>
                    <MetricCard
                      label="Avg Latency"
                      value={`${Math.round(detail.summary?.avg_latency_ms || 0)}ms`}
                      tone="warning"
                    />
                  </Col>
                </Row>

                <Alert
                  type={detail.issue === "healthy" ? "success" : "error"}
                  showIcon
                  style={{ marginBottom: 12 }}
                  message="Root Cause"
                  description={detail.root_cause}
                />
                <Alert
                  type="info"
                  showIcon
                  style={{ marginBottom: 14 }}
                  message="Suggestion"
                  description={
                    <div>
                      <div style={{ marginBottom: 8 }}>{detail.suggestion}</div>
                      <Space wrap>
                        {taskId ? (
                          <Button size="small" onClick={() => navigate(`/tasks/${taskId}`)}>
                            任务详情
                          </Button>
                        ) : null}
                        <Button
                          size="small"
                          icon={<ApartmentOutlined />}
                          onClick={() => {
                            const tid = detail.token_curve?.[0]?.trace_id;
                            navigate(tid ? `/traces?id=${tid}` : "/traces");
                          }}
                        >
                          打开 Trace
                        </Button>
                        <Button
                          size="small"
                          type="primary"
                          ghost
                          onClick={() => navigate("/tasks/create")}
                        >
                          调整配置并新建
                        </Button>
                      </Space>
                    </div>
                  }
                />

                <Row gutter={[14, 14]}>
                  <Col xs={24} md={8}>
                    <Panel title="Confidence">
                      <EChart option={confGauge} height={240} />
                    </Panel>
                  </Col>
                  <Col xs={24} md={16}>
                    <Panel
                      title={
                        <>
                          <ThunderboltOutlined /> Token / Latency Drift
                        </>
                      }
                      extra={
                        <Tag>
                          prompts: {(detail.prompt_versions || []).join(", ") || "default"}
                        </Tag>
                      }
                    >
                      <EChart option={dualOption} height={240} />
                    </Panel>
                  </Col>
                  <Col xs={24} md={12}>
                    <Panel
                      title={
                        <>
                          <NodeIndexOutlined /> Call Chain
                        </>
                      }
                    >
                      <AgentTopologyFlow
                        layout="horizontal"
                        nodes={(detail.topology?.nodes || []).map((n) => ({
                          id: n.id,
                          label: n.label,
                          status: n.status,
                        }))}
                        edges={detail.topology?.edges || []}
                        height={300}
                        showMiniMap={false}
                      />
                    </Panel>
                  </Col>
                  <Col xs={24} md={12}>
                    <Panel
                      title={
                        <>
                          <ExperimentOutlined /> Issue Confidence
                        </>
                      }
                    >
                      <EChart option={issueBar} height={300} />
                    </Panel>
                  </Col>
                  <Col span={24}>
                    <Panel
                      title="Issue Breakdown & Evidence"
                      extra={
                        <Segmented
                          size="small"
                          value={focus}
                          onChange={(v) => setFocus(String(v))}
                          options={issueTabs}
                        />
                      }
                    >
                      {issues.length === 0 ? (
                        <Empty description="无匹配 issue" />
                      ) : (
                        issues.map((iss, idx) => (
                          <div
                            key={`${iss.issue}-${idx}`}
                            className="ic-panel"
                            style={{ padding: 14, marginBottom: 12 }}
                          >
                            <Space wrap style={{ marginBottom: 8 }}>
                              <Tag color={ISSUE_COLOR[iss.issue] || "default"}>
                                {ISSUE_LABEL[iss.issue] || iss.issue}
                              </Tag>
                              <Progress
                                percent={Math.round(iss.confidence * 100)}
                                size="small"
                                style={{ width: 140 }}
                                strokeColor="#00D4FF"
                              />
                            </Space>
                            <Paragraph style={{ marginBottom: 6, fontSize: 13 }}>
                              <Text type="secondary">Root cause · </Text>
                              {iss.root_cause}
                            </Paragraph>
                            <Paragraph
                              type="secondary"
                              style={{ marginBottom: 8, fontSize: 12 }}
                            >
                              <Text type="secondary">Suggestion · </Text>
                              {iss.suggestion}
                            </Paragraph>
                            {"evidence" in iss &&
                            iss.evidence &&
                            typeof iss.evidence === "object" ? (
                              <Collapse
                                size="small"
                                items={[
                                  {
                                    key: "ev",
                                    label: "Evidence payload",
                                    children: (
                                      <pre className="ic-code" style={{ maxHeight: 200 }}>
                                        {JSON.stringify(iss.evidence, null, 2)}
                                      </pre>
                                    ),
                                  },
                                ]}
                              />
                            ) : null}
                          </div>
                        ))
                      )}
                      <Space wrap>
                        {taskId ? (
                          <Button type="link" onClick={() => navigate(`/tasks/${taskId}`)}>
                            打开任务详情 →
                          </Button>
                        ) : null}
                        <Button type="link" onClick={() => navigate("/analytics")}>
                          查看 Analytics →
                        </Button>
                      </Space>
                    </Panel>
                  </Col>
                </Row>
              </>
            )}
          </Spin>
        </Col>
      </Row>
    </div>
  );
}

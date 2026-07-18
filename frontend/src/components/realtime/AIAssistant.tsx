/* Floating AI Optimization Assistant */

import { useCallback, useEffect, useState } from "react";
import { Button, Space, Tag, Typography } from "antd";
import {
  RobotOutlined,
  CloseOutlined,
  ThunderboltOutlined,
  BugOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useDiagnosisList, useDashboardOverview } from "@/hooks";

const { Text, Paragraph } = Typography;

type Msg = { title: string; body: string; issue?: string };

export function AIAssistant() {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const navigate = useNavigate();
  const { data: diagnoses } = useDiagnosisList(5);
  const { data: overview } = useDashboardOverview(7);

  const rebuild = useCallback(() => {
    const next: Msg[] = [];
    if (overview) {
      if (overview.health < 90) {
        next.push({
          title: "AI Health 偏低",
          body: `当前 Health ${overview.health}% 。建议检查 Failure Rate 与慢任务，并打开 Diagnosis Center。`,
          issue: "health",
        });
      }
      if ((overview.failure_rate ?? 0) > 0.15) {
        next.push({
          title: "失败率升高",
          body: `Failure Rate ${((overview.failure_rate || 0) * 100).toFixed(1)}%。优先排查 Tool Failure 与超时。`,
          issue: "failure",
        });
      }
      if ((overview.latency ?? 0) > 3) {
        next.push({
          title: "延迟告警",
          body: `平均延迟 ${overview.latency?.toFixed(2)}s。建议降低 max_iterations 或优化慢工具。`,
          issue: "latency",
        });
      }
    }
    for (const d of diagnoses?.items || []) {
      if (d.issue === "healthy") continue;
      next.push({
        title: `发现：${d.issue}`,
        body: `原因：${d.root_cause}\n建议：${d.suggestion}`,
        issue: d.issue,
      });
    }
    if (!next.length) {
      next.push({
        title: "系统运行平稳",
        body: "未发现显著异常。可在 Trace Explorer 深入单次调用，或在 Analytics 对比模型能力。",
      });
    }
    setMsgs(next.slice(0, 6));
  }, [diagnoses, overview]);

  useEffect(() => {
    if (open) rebuild();
  }, [open, rebuild]);

  return (
    <>
      {open ? (
        <div className="ic-assistant-panel" role="dialog" aria-label="AI Assistant">
          <div className="ic-assistant-header">
            <Space>
              <RobotOutlined style={{ color: "#00D4FF" }} />
              <Text strong style={{ color: "var(--af-text)" }}>
                AI Optimization Assistant
              </Text>
              <Tag color="cyan">beta</Tag>
            </Space>
            <Button
              type="text"
              size="small"
              icon={<CloseOutlined />}
              onClick={() => setOpen(false)}
              aria-label="Close assistant"
            />
          </div>
          <div className="ic-assistant-body">
            {msgs.map((m, i) => (
              <div key={i} className="ic-assistant-msg">
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  {m.issue && m.issue !== "healthy" ? (
                    <BugOutlined style={{ color: "#FF3864" }} />
                  ) : (
                    <ThunderboltOutlined style={{ color: "#00FF9D" }} />
                  )}
                  <strong>{m.title}</strong>
                </div>
                <Paragraph style={{ marginBottom: 8, whiteSpace: "pre-wrap", fontSize: 12.5 }}>
                  {m.body}
                </Paragraph>
                {m.issue && m.issue !== "healthy" ? (
                  <Button
                    size="small"
                    type="link"
                    onClick={() => {
                      setOpen(false);
                      navigate("/diagnosis");
                    }}
                  >
                    打开故障诊断 →
                  </Button>
                ) : null}
              </div>
            ))}
            <Space wrap>
              <Button size="small" onClick={() => navigate("/traces")}>
                Trace Explorer
              </Button>
              <Button size="small" onClick={() => navigate("/analytics")}>
                Analytics
              </Button>
              <Button size="small" onClick={() => rebuild()}>
                重新分析
              </Button>
            </Space>
          </div>
        </div>
      ) : null}
      <button
        type="button"
        className="ic-assistant-fab"
        onClick={() => setOpen((o) => !o)}
        title="AI Assistant"
        aria-label="Open AI Assistant"
      >
        <RobotOutlined />
      </button>
    </>
  );
}

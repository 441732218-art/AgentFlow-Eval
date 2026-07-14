/* (c) 2026 AgentFlow-Eval */
/* Vertical timeline for ReAct steps */

import React, { useState } from "react";
import { Timeline, Tag, Typography, Button, Space, Empty, message } from "antd";
import {
  BulbOutlined,
  ToolOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  CopyOutlined,
  DownOutlined,
  UpOutlined,
} from "@ant-design/icons";
import type { TraceStep } from "@/types";

const { Text, Paragraph } = Typography;

interface StepLogPanelProps {
  steps: TraceStep[];
}

const stepIcons: Record<string, React.ReactNode> = {
  thought: <BulbOutlined />,
  action: <ToolOutlined />,
  observation: <EyeOutlined />,
  final_answer: <CheckCircleOutlined />,
};

const stepColors: Record<string, string> = {
  thought: "#38bdf8",
  action: "#fbbf24",
  observation: "#34d399",
  final_answer: "#818cf8",
};

const stepLabels: Record<string, string> = {
  thought: "Thought",
  action: "Action",
  observation: "Observation",
  final_answer: "Final Answer",
};

function stepTypeOf(step: TraceStep): string {
  return step.type || step.role || step.action || "thought";
}

function stepBody(step: TraceStep): string {
  return (
    step.content ||
    step.observation ||
    step.thought ||
    step.action_input ||
    step.tool_input ||
    ""
  );
}

const StepLogPanel: React.FC<StepLogPanelProps> = ({ steps }) => {
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  if (!steps?.length) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无步骤日志" />;
  }

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(steps, null, 2));
      message.success("步骤 JSON 已复制");
    } catch {
      message.error("复制失败");
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <Button size="small" type="text" icon={<CopyOutlined />} onClick={copyAll}>
          复制全部
        </Button>
      </div>
      <Timeline
        items={steps.map((step, idx) => {
          const t = stepTypeOf(step);
          const color = stepColors[t] || stepColors.thought;
          const body = stepBody(step);
          const isLong = body.length > 220;
          const open = !!expanded[idx];
          const shown = isLong && !open ? body.slice(0, 220) + "…" : body;

          return {
            key: idx,
            color,
            dot: (
              <div
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: 8,
                  background: `${color}22`,
                  border: `1px solid ${color}66`,
                  display: "grid",
                  placeItems: "center",
                  color,
                  fontSize: 13,
                }}
              >
                {stepIcons[t] || stepIcons.thought}
              </div>
            ),
            children: (
              <div
                className="af-card-hover"
                style={{
                  padding: "12px 14px",
                  borderRadius: 12,
                  border: "1px solid var(--af-border)",
                  background: "var(--af-bg-muted)",
                  marginBottom: 4,
                }}
              >
                <Space wrap style={{ marginBottom: 8 }}>
                  <Tag
                    style={{
                      margin: 0,
                      color,
                      borderColor: `${color}55`,
                      background: `${color}18`,
                    }}
                  >
                    {stepLabels[t] || t}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    #{idx + 1}
                  </Text>
                  {step.tokens != null && step.tokens > 0 && (
                    <Tag style={{ margin: 0 }}>{step.tokens} tok</Tag>
                  )}
                </Space>

                {(step.tool_name || step.action) &&
                  step.action !== "final_answer" &&
                  t !== "thought" && (
                    <div style={{ marginBottom: 6 }}>
                      <Text code style={{ fontSize: 12 }}>
                        {step.tool_name || step.action}
                      </Text>
                    </div>
                  )}

                {shown && (
                  <Paragraph
                    style={{
                      margin: 0,
                      fontSize: 13,
                      whiteSpace: "pre-wrap",
                      color: "var(--af-text-secondary)",
                      lineHeight: 1.55,
                    }}
                  >
                    {shown}
                  </Paragraph>
                )}

                {isLong && (
                  <Button
                    type="link"
                    size="small"
                    style={{ padding: 0, marginTop: 4, height: "auto" }}
                    icon={open ? <UpOutlined /> : <DownOutlined />}
                    onClick={() => setExpanded((e) => ({ ...e, [idx]: !open }))}
                  >
                    {open ? "收起" : "展开全部"}
                  </Button>
                )}
              </div>
            ),
          };
        })}
      />
    </div>
  );
};

export default StepLogPanel;

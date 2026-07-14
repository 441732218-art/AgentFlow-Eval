/* (c) 2026 AgentFlow-Eval */
/* Modern scoring results card */

import React from "react";
import { Card, Progress, Typography, Space, Empty, Button, message } from "antd";
import { CopyOutlined, TrophyOutlined } from "@ant-design/icons";
import type { MetricScore } from "@/types";

const { Text, Paragraph } = Typography;

interface ScoreCardProps {
  metricScores: MetricScore[];
  loading?: boolean;
}

const metricLabels: Record<string, string> = {
  tool_accuracy: "工具调用准确率",
  answer_correctness: "答案准确性",
  reasoning_coherence: "推理连贯性",
};

const metricColors: Record<string, string> = {
  tool_accuracy: "#38bdf8",
  answer_correctness: "#34d399",
  reasoning_coherence: "#818cf8",
};

const metricMax: Record<string, number> = {
  tool_accuracy: 40,
  answer_correctness: 40,
  reasoning_coherence: 20,
};

const ScoreCard: React.FC<ScoreCardProps> = ({ metricScores, loading }) => {
  if (loading) {
    return (
      <Card className="af-glass" loading title="评分结果">
        <p>Loading…</p>
      </Card>
    );
  }

  if (!metricScores.length) {
    return (
      <Card className="af-glass" title="评分结果">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无评分" />
      </Card>
    );
  }

  const total = metricScores.reduce((sum, ms) => sum + ms.score, 0);
  const reason = metricScores[0]?.reason;

  const copyScores = async () => {
    const payload = {
      total,
      scores: Object.fromEntries(metricScores.map((m) => [m.metric_name, m.score])),
      reason,
    };
    try {
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      message.success("评分已复制");
    } catch {
      message.error("复制失败");
    }
  };

  return (
    <Card
      className="af-glass"
      title={
        <Space>
          <TrophyOutlined style={{ color: "var(--af-gold)" }} />
          <span>评分结果</span>
        </Space>
      }
      extra={
        <Button type="text" size="small" icon={<CopyOutlined />} onClick={copyScores}>
          复制
        </Button>
      }
    >
      <div style={{ textAlign: "center", marginBottom: 20 }}>
        <Progress
          type="dashboard"
          percent={Math.min(100, Math.round(total))}
          strokeColor={{ "0%": "#38bdf8", "100%": "#818cf8" }}
          format={() => (
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, lineHeight: 1.1 }}>{Math.round(total)}</div>
              <div style={{ fontSize: 11, color: "var(--af-text-muted)" }}>总分</div>
            </div>
          )}
          size={130}
        />
      </div>

      {metricScores.map((ms) => {
        const max = metricMax[ms.metric_name] || 100;
        const pct = Math.min(100, Math.round((ms.score / max) * 100));
        const color = metricColors[ms.metric_name] || "#38bdf8";
        return (
          <div key={ms.id} style={{ marginBottom: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <Text style={{ fontSize: 13 }}>
                {metricLabels[ms.metric_name] || ms.metric_name}
              </Text>
              <Text strong style={{ color, fontVariantNumeric: "tabular-nums" }}>
                {ms.score}
                <Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
                  {" "}
                  / {max}
                </Text>
              </Text>
            </div>
            <Progress
              percent={pct}
              strokeColor={color}
              size="small"
              showInfo={false}
              trailColor="var(--af-bg-muted)"
            />
          </div>
        );
      })}

      {reason && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: 10,
            background: "var(--af-bg-muted)",
            border: "1px solid var(--af-border)",
          }}
        >
          <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 4 }}>
            评语
          </Text>
          <Paragraph
            style={{ margin: 0, fontSize: 12, whiteSpace: "pre-wrap", color: "var(--af-text-secondary)" }}
          >
            {reason}
          </Paragraph>
        </div>
      )}
    </Card>
  );
};

export default ScoreCard;

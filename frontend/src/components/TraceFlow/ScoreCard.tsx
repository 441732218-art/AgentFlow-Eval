/* (c) 2026 AgentFlow-Eval */
/* Score results card — dimension max/label driven by scorecard (Phase 3) */

import React, { useMemo } from "react";
import { Card, Progress, Typography, Space, Empty, Button, message, Tag } from "antd";
import { CopyOutlined, TrophyOutlined } from "@ant-design/icons";
import type { MetricScore } from "@/types";

const { Text, Paragraph } = Typography;

export interface ScorecardDimensionMeta {
  key: string;
  label?: string;
  weight?: number;
  description?: string;
}

interface ScoreCardProps {
  metricScores: MetricScore[];
  loading?: boolean;
  /** Optional scorecard dimensions for labels/max weights */
  dimensions?: ScorecardDimensionMeta[];
  scorecardName?: string;
}

/**
 * 评测规则配置项
 * 支持自定义权重、阈值与评估器，实现灵活的多维评价体系
 */
interface ScoreRuleConfig {
  /** 指标标识符 */
  metric: string;
  /** 权重系数 (0-1)，所有规则权重之和应为1 */
  weight: number;
  /** 评估器类型: llm_judge | rule_based | human_review */
  evaluator: 'llm_judge' | 'rule_based' | 'human_review';
  /** 合格阈值，低于此值触发告警或人工复核 */
  threshold?: number;
  /** 评分说明（用于报告生成） */
  description?: string;
}

/**
 * 默认评测规则配置（可从运行时从后端加载覆盖）
 */
const DEFAULT_SCORE_RULES: ScoreRuleConfig[] = [
  { metric: 'tool_accuracy', weight: 0.4, evaluator: 'llm_judge', threshold: 0.7, description: '工具调用参数提取与执行结果正确性' },
  { metric: 'answer_correctness', weight: 0.4, evaluator: 'llm_judge', threshold: 0.8, description: '最终答案与标准答案的语义一致性' },
  { metric: 'reasoning_coherence', weight: 0.2, evaluator: 'rule_based', threshold: 0.6, description: '思维链步骤完整性与逻辑连贯性' },
];

const FALLBACK_LABELS: Record<string, string> = {
  tool_accuracy: "工具调用准确率",
  answer_correctness: "答案准确性",
  reasoning_coherence: "推理连贯性",
};

/** 从 DEFAULT_SCORE_RULES 派生的回退权重映射 */
export const FALLBACK_MAX: Record<string, number> = Object.fromEntries(
  DEFAULT_SCORE_RULES.map((rule) => [rule.metric, Math.round(rule.weight * 100)])
);

const COLORS = ["#38bdf8", "#34d399", "#818cf8", "#fbbf24", "#f472b6", "#a78bfa"];

const ScoreCard: React.FC<ScoreCardProps> = ({
  metricScores,
  loading,
  dimensions,
  scorecardName,
}) => {
  const dimMap = useMemo(() => {
    const m = new Map<string, ScorecardDimensionMeta>();
    for (const d of dimensions || []) {
      m.set(d.key, d);
    }
    return m;
  }, [dimensions]);

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
  const maxTotal =
    dimensions && dimensions.length
      ? dimensions.reduce((s, d) => s + (d.weight || 0), 0) || 100
      : 100;
  const reason = metricScores[0]?.reason;

  const copyScores = async () => {
    const payload = {
      total,
      scores: Object.fromEntries(metricScores.map((m) => [m.metric_name, m.score])),
      reason,
      scorecard: scorecardName,
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
          {scorecardName ? <Tag>{scorecardName}</Tag> : null}
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
          percent={Math.min(100, Math.round((total / maxTotal) * 100))}
          strokeColor={{ "0%": "#38bdf8", "100%": "#818cf8" }}
          format={() => (
            <div>
              <div style={{ fontSize: 28, fontWeight: 800, lineHeight: 1.1 }}>
                {Math.round(total * 10) / 10}
              </div>
              <div style={{ fontSize: 11, color: "var(--af-text-muted)" }}>
                / {Math.round(maxTotal)}
              </div>
            </div>
          )}
          size={130}
        />
      </div>

      {metricScores.map((ms, idx) => {
        const meta = dimMap.get(ms.metric_name);
        const max =
          meta?.weight ??
          FALLBACK_MAX[ms.metric_name] ??
          Math.max(ms.score, 1);
        const pct = Math.min(100, Math.round((ms.score / max) * 100));
        const color = COLORS[idx % COLORS.length];
        const label =
          meta?.label || FALLBACK_LABELS[ms.metric_name] || ms.metric_name;
        return (
          <div key={ms.id || ms.metric_name} style={{ marginBottom: 14 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 6,
              }}
            >
              <Text style={{ fontSize: 13 }}>{label}</Text>
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
            />
            {meta?.description ? (
              <Paragraph type="secondary" style={{ fontSize: 11, margin: "4px 0 0" }}>
                {meta.description}
              </Paragraph>
            ) : null}
          </div>
        );
      })}

      {reason ? (
        <Paragraph
          type="secondary"
          style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}
        >
          {reason}
        </Paragraph>
      ) : null}
    </Card>
  );
};

export default ScoreCard;

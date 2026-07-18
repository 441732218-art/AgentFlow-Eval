/* (c) 2026 AgentFlow-Eval — compact quota bar for Dashboard / header */

import React, { useMemo } from "react";
import { Card, Col, Progress, Row, Space, Tag, Typography, Button } from "antd";
import { AccountBookOutlined, RightOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useBillingQuota } from "@/hooks";
import { useI18nStore } from "@/i18n";

const { Text } = Typography;

function pct(used: number, limit: number): number {
  if (!limit || limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export const QuotaStrip: React.FC<{ compact?: boolean }> = ({ compact }) => {
  const t = useI18nStore((s) => s.t);
  const navigate = useNavigate();
  const { data: quota, isLoading, isError } = useBillingQuota();

  const taskPct = useMemo(
    () => pct(quota?.task_used ?? 0, quota?.task_limit ?? 1),
    [quota]
  );
  const tokenPct = useMemo(
    () => pct(Number(quota?.token_used ?? 0), quota?.token_limit ?? 1),
    [quota]
  );

  if (isError) return null;

  const plan = (quota?.plan_code || "free").toUpperCase();
  const warn = taskPct >= 90 || tokenPct >= 90;

  return (
    <Card
      className="af-glass"
      size="small"
      loading={isLoading}
      style={{ marginBottom: compact ? 12 : 16 }}
      styles={{ body: { padding: compact ? "12px 16px" : 16 } }}
    >
      <Row gutter={[16, 8]} align="middle">
        <Col xs={24} sm={6} md={5}>
          <Space>
            <AccountBookOutlined style={{ color: "var(--af-primary, #38bdf8)" }} />
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {t("billing.currentPlan")}
              </Text>
              <div>
                <Tag color={warn ? "orange" : "blue"}>{plan}</Tag>
                {!quota?.billing_enabled && (
                  <Tag>{t("billing.flagOffShort")}</Tag>
                )}
              </div>
            </div>
          </Space>
        </Col>
        <Col xs={24} sm={8} md={7}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t("billing.taskQuota")}: {quota?.task_used ?? 0}/{quota?.task_limit ?? "—"}
          </Text>
          <Progress
            percent={taskPct}
            size="small"
            showInfo={false}
            status={taskPct >= 90 ? "exception" : "active"}
          />
        </Col>
        <Col xs={24} sm={8} md={7}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t("billing.tokenQuota")}: {Math.round(Number(quota?.token_used ?? 0))}/
            {quota?.token_limit ?? "—"}
          </Text>
          <Progress
            percent={tokenPct}
            size="small"
            showInfo={false}
            status={tokenPct >= 90 ? "exception" : "active"}
          />
        </Col>
        <Col xs={24} sm={24} md={5} style={{ textAlign: "right" }}>
          <Button
            type="link"
            size="small"
            onClick={() => navigate("/billing")}
            icon={<RightOutlined />}
          >
            {t("nav.billing")}
          </Button>
        </Col>
      </Row>
    </Card>
  );
};

export default QuotaStrip;

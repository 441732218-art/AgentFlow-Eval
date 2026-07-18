/* (c) 2026 AgentFlow-Eval — compact quota chip in app header */

import React, { useMemo } from "react";
import { Badge, Button, Progress, Space, Tooltip, Typography } from "antd";
import { AccountBookOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useBillingQuota } from "@/hooks";
import { useI18nStore } from "@/i18n";

const { Text } = Typography;

function pct(used: number, limit: number): number {
  if (!limit || limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export const HeaderQuotaBadge: React.FC = () => {
  const t = useI18nStore((s) => s.t);
  const navigate = useNavigate();
  const { data: quota, isLoading, isError } = useBillingQuota();

  const taskPct = useMemo(
    () => pct(quota?.task_used ?? 0, quota?.task_limit ?? 1),
    [quota]
  );
  const warn = taskPct >= 85;

  if (isError) return null;

  const plan = (quota?.plan_code || "free").toUpperCase();
  const title = (
    <div style={{ minWidth: 180 }}>
      <div>
        {t("billing.currentPlan")}: <b>{plan}</b>
      </div>
      <div style={{ marginTop: 6 }}>
        {t("billing.taskQuota")}: {quota?.task_used ?? "—"}/{quota?.task_limit ?? "—"}
      </div>
      <Progress
        percent={taskPct}
        size="small"
        showInfo={false}
        status={warn ? "exception" : "active"}
        style={{ marginTop: 4 }}
      />
      <div style={{ marginTop: 4, fontSize: 12, opacity: 0.85 }}>
        {t("billing.tokenQuota")}: {Math.round(Number(quota?.token_used ?? 0))}/
        {quota?.token_limit ?? "—"}
      </div>
      {!quota?.billing_enabled && (
        <div style={{ marginTop: 4, fontSize: 11 }}>{t("billing.flagOffShort")}</div>
      )}
    </div>
  );

  return (
    <Tooltip title={title} placement="bottomRight">
      <Badge dot={warn} offset={[-4, 4]}>
        <Button
          type="text"
          loading={isLoading}
          onClick={() => navigate("/billing")}
          style={{
            color: warn ? "var(--af-danger, #f87171)" : "var(--af-text-secondary)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            paddingInline: 10,
          }}
        >
          <AccountBookOutlined />
          <Space size={4} style={{ lineHeight: 1 }}>
            <Text style={{ color: "inherit", fontSize: 12 }}>{plan}</Text>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {quota?.task_used ?? 0}/{quota?.task_limit ?? "—"}
            </Text>
          </Space>
        </Button>
      </Badge>
    </Tooltip>
  );
};

export default HeaderQuotaBadge;

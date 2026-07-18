/* (c) 2026 AgentFlow-Eval — Billing / usage / plans */

import React, { useEffect, useMemo } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Progress,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  DollarOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import {
  useBillingInvoices,
  useBillingPlans,
  useBillingQuota,
  useBillingUsage,
  useCheckoutPlan,
  useDraftInvoice,
  useSubscribePlan,
} from "@/hooks";
import { useI18nStore } from "@/i18n";
import { Can } from "@/auth";
import type { BillingPlan, UsageItem } from "@/api/endpoints/billing";

const { Text, Paragraph } = Typography;

function pct(used: number, limit: number): number {
  if (!limit || limit <= 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

function formatPrice(cents: number): string {
  if (cents <= 0) return "Free";
  return `$${(cents / 100).toFixed(2)}/mo`;
}

const BillingPage: React.FC = () => {
  const t = useI18nStore((s) => s.t);
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: quota, isLoading: qLoading, refetch: refetchQuota } = useBillingQuota();
  const { data: plansData, isLoading: pLoading } = useBillingPlans();
  const { data: usageData, isLoading: uLoading } = useBillingUsage(50);
  const { data: invData, isLoading: iLoading } = useBillingInvoices();
  const subscribe = useSubscribePlan();
  const checkout = useCheckoutPlan();
  const draftInv = useDraftInvoice();

  useEffect(() => {
    const checkoutState = searchParams.get("checkout");
    if (checkoutState === "success") {
      message.success(t("billing.checkoutSuccess"));
      void refetchQuota();
      searchParams.delete("checkout");
      searchParams.delete("session_id");
      setSearchParams(searchParams, { replace: true });
    } else if (checkoutState === "cancel") {
      message.info(t("billing.checkoutCancel"));
      searchParams.delete("checkout");
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, refetchQuota, t]);

  const plans = plansData?.items ?? [];
  const usage = usageData?.items ?? [];
  const invoices = invData?.items ?? [];

  const taskPct = useMemo(
    () => pct(quota?.task_used ?? 0, quota?.task_limit ?? 1),
    [quota]
  );
  const tokenPct = useMemo(
    () => pct(quota?.token_used ?? 0, quota?.token_limit ?? 1),
    [quota]
  );

  if (qLoading && pLoading) {
    return <PageSkeleton variant="cards" />;
  }

  return (
    <div className="ic-page af-page">
      <PageHeader
        title={t("billing.title")}
        subtitle={t("billing.subtitle")}
        icon={<DollarOutlined />}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void refetchQuota()}
            >
              {t("common.refresh")}
            </Button>
            <Can perm="system:config">
              <Button
                icon={<FileTextOutlined />}
                loading={draftInv.isPending}
                onClick={() => {
                  draftInv.mutate(undefined, {
                    onSuccess: () => message.success(t("billing.invoiceDraftOk")),
                    onError: (e: Error) => message.error(e.message),
                  });
                }}
              >
                {t("billing.draftInvoice")}
              </Button>
            </Can>
          </Space>
        }
      />

      {!quota?.billing_enabled && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={t("billing.flagOff")}
          description={t("billing.flagOffDesc")}
        />
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <Card className="af-glass" styles={{ body: { padding: 18 } }}>
            <Text type="secondary">{t("billing.currentPlan")}</Text>
            <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>
              {(quota?.plan_code || "free").toUpperCase()}
            </div>
            <Text type="secondary">
              {t("billing.period")}: {quota?.period || "—"} ·{" "}
              {quota?.subscription_status || "none"}
            </Text>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="af-glass" styles={{ body: { padding: 18 } }}>
            <Text type="secondary">{t("billing.taskQuota")}</Text>
            <div style={{ fontSize: 22, fontWeight: 600, marginTop: 4 }}>
              {quota?.task_used ?? 0} / {quota?.task_limit ?? "—"}
            </div>
            <Progress percent={taskPct} size="small" status={taskPct >= 90 ? "exception" : "active"} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card className="af-glass" styles={{ body: { padding: 18 } }}>
            <Text type="secondary">{t("billing.tokenQuota")}</Text>
            <div style={{ fontSize: 22, fontWeight: 600, marginTop: 4 }}>
              {Math.round(quota?.token_used ?? 0)} / {quota?.token_limit ?? "—"}
            </div>
            <Progress
              percent={tokenPct}
              size="small"
              status={tokenPct >= 90 ? "exception" : "active"}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={t("billing.plans")}
        className="af-glass"
        style={{ marginBottom: 16 }}
        loading={pLoading}
      >
        <Row gutter={[16, 16]}>
          {plans.map((p: BillingPlan) => {
            const current = p.code === quota?.plan_code;
            return (
              <Col xs={24} md={8} key={p.id}>
                <Card
                  size="small"
                  className="af-card-hover"
                  style={{
                    height: "100%",
                    borderColor: current ? "var(--af-primary, #38bdf8)" : undefined,
                  }}
                >
                  <Space direction="vertical" style={{ width: "100%" }}>
                    <Space>
                      <DollarOutlined />
                      <Text strong>{p.name}</Text>
                      {current && <Tag color="blue">{t("billing.current")}</Tag>}
                    </Space>
                    <Text type="secondary">{p.description}</Text>
                    <div style={{ fontSize: 20, fontWeight: 700 }}>
                      {formatPrice(p.price_month_cents)}
                    </div>
                    <Text type="secondary">
                      {p.task_quota} tasks · {p.token_quota.toLocaleString()} tokens
                    </Text>
                    <Can perm="system:config">
                      <Button
                        type={current ? "default" : "primary"}
                        block
                        disabled={current}
                        loading={
                          subscribe.isPending ||
                          (checkout.isPending && checkout.variables === p.code)
                        }
                        icon={<ThunderboltOutlined />}
                        onClick={() => {
                          // Free / zero-price: direct subscribe; paid: Checkout (mock auto-confirm)
                          if (!p.price_month_cents || p.code === "free") {
                            subscribe.mutate(p.code, {
                              onSuccess: () =>
                                message.success(
                                  `${t("billing.subscribeOk")}: ${p.code}`
                                ),
                              onError: (e: Error) => message.error(e.message),
                            });
                            return;
                          }
                          checkout.mutate(p.code, {
                            onSuccess: (data) => {
                              const url = data.checkout?.url;
                              if (
                                data.checkout?.mode === "live" &&
                                url &&
                                !data.mock_confirmed
                              ) {
                                window.location.href = url;
                                return;
                              }
                              message.success(
                                `${t("billing.checkoutOk")}: ${p.code}`
                              );
                            },
                            onError: (e: Error) => message.error(e.message),
                          });
                        }}
                      >
                        {current
                          ? t("billing.current")
                          : p.price_month_cents > 0
                            ? t("billing.checkout")
                            : t("billing.subscribe")}
                      </Button>
                    </Can>
                  </Space>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title={t("billing.usage")} className="af-glass" loading={uLoading}>
            <Table<UsageItem>
              size="small"
              rowKey="id"
              pagination={{ pageSize: 8 }}
              dataSource={usage}
              locale={{ emptyText: t("billing.usageEmpty") }}
              columns={[
                { title: t("billing.metric"), dataIndex: "metric", width: 100 },
                {
                  title: t("billing.quantity"),
                  dataIndex: "quantity",
                  width: 90,
                  render: (v: number) => (Number.isInteger(v) ? v : v.toFixed(2)),
                },
                {
                  title: "Ref",
                  key: "ref",
                  render: (_, r) =>
                    r.ref_type ? `${r.ref_type}:${r.ref_id || ""}` : "—",
                },
                {
                  title: "Trace",
                  dataIndex: "trace_id",
                  ellipsis: true,
                  render: (v: string | null) => v || "—",
                },
                {
                  title: t("billing.time"),
                  dataIndex: "created_at",
                  width: 180,
                  render: (v: string | null) =>
                    v ? new Date(v).toLocaleString() : "—",
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title={t("billing.invoices")} className="af-glass" loading={iLoading}>
            {invoices.length === 0 ? (
              <Paragraph type="secondary">{t("billing.invoiceEmpty")}</Paragraph>
            ) : (
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={invoices}
                columns={[
                  { title: t("billing.period"), dataIndex: "period", width: 90 },
                  {
                    title: t("billing.amount"),
                    dataIndex: "amount_cents",
                    render: (c: number) => `$${(c / 100).toFixed(2)}`,
                  },
                  {
                    title: t("billing.status"),
                    dataIndex: "status",
                    render: (s: string) => <Tag>{s}</Tag>,
                  },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default BillingPage;

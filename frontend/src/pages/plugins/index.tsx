/* (c) 2026 AgentFlow-Eval — Plugin marketplace & lifecycle admin */

import React, { useCallback, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  message,
  Tooltip,
} from "antd";
import {
  AppstoreOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { Can } from "@/auth";
import { pluginsApi, type MarketPlugin } from "@/api/endpoints/plugins";
import { useI18nStore } from "@/i18n";

const { Text, Paragraph } = Typography;

function priceLabel(cents?: number, isPaid?: boolean): string {
  if (!isPaid && (!cents || cents <= 0)) return "Free";
  return `$${((cents || 0) / 100).toFixed(2)}`;
}

const PluginsPage: React.FC = () => {
  const t = useI18nStore((s) => s.t);
  const qc = useQueryClient();
  const [busyId, setBusyId] = useState<string | null>(null);

  const marketQ = useQuery({
    queryKey: ["plugins", "market"],
    queryFn: () => pluginsApi.market(),
    staleTime: 30_000,
  });
  const installedQ = useQuery({
    queryKey: ["plugins", "installed"],
    queryFn: () => pluginsApi.list(),
    staleTime: 15_000,
  });
  const statusQ = useQuery({
    queryKey: ["plugins", "status"],
    queryFn: () => pluginsApi.status(),
    staleTime: 15_000,
  });

  const refreshAll = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["plugins"] });
  }, [qc]);

  const installM = useMutation({
    mutationFn: (id: string) => pluginsApi.install(id, true),
    onSuccess: () => {
      message.success(t("plugins.installOk"));
      refreshAll();
    },
    onError: (e: Error) => message.error(e.message),
    onSettled: () => setBusyId(null),
  });
  const uninstallM = useMutation({
    mutationFn: (id: string) => pluginsApi.uninstall(id),
    onSuccess: () => {
      message.success(t("plugins.uninstallOk"));
      refreshAll();
    },
    onError: (e: Error) => message.error(e.message),
    onSettled: () => setBusyId(null),
  });
  const activateM = useMutation({
    mutationFn: (id: string) => pluginsApi.activate(id),
    onSuccess: () => {
      message.success(t("plugins.activateOk"));
      refreshAll();
    },
    onError: (e: Error) => message.error(e.message),
    onSettled: () => setBusyId(null),
  });
  const deactivateM = useMutation({
    mutationFn: (id: string) => pluginsApi.deactivate(id),
    onSuccess: () => {
      message.success(t("plugins.deactivateOk"));
      refreshAll();
    },
    onError: (e: Error) => message.error(e.message),
    onSettled: () => setBusyId(null),
  });

  if (marketQ.isLoading && installedQ.isLoading) {
    return <PageSkeleton variant="cards" />;
  }

  const market = marketQ.data?.items ?? [];
  const planCode = marketQ.data?.plan_code || "free";
  const installed = installedQ.data?.items ?? [];
  const status = statusQ.data as
    | {
        runners?: unknown[];
        judges?: unknown[];
        tools?: unknown[];
        hooks?: unknown[];
      }
    | undefined;

  return (
    <div className="ic-page af-page">
      <PageHeader
        title={t("plugins.title")}
        subtitle={t("plugins.subtitle")}
        icon={<AppstoreOutlined />}
        extra={
          <Button icon={<ReloadOutlined />} onClick={refreshAll}>
            {t("common.refresh")}
          </Button>
        }
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={
          <span>
            {t("plugins.planHint")}: <Tag color="blue">{planCode.toUpperCase()}</Tag>
          </span>
        }
        description={t("plugins.planHintDesc")}
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} md={6}>
          <Card size="small" className="af-glass">
            <Text type="secondary">Runners</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {status?.runners?.length ?? 0}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" className="af-glass">
            <Text type="secondary">Judges</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {status?.judges?.length ?? 0}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" className="af-glass">
            <Text type="secondary">Tools</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {status?.tools?.length ?? 0}
            </div>
          </Card>
        </Col>
        <Col xs={12} md={6}>
          <Card size="small" className="af-glass">
            <Text type="secondary">Hooks</Text>
            <div style={{ fontSize: 22, fontWeight: 700 }}>
              {status?.hooks?.length ?? 0}
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <AppstoreOutlined />
            {t("plugins.market")}
          </Space>
        }
        className="af-glass"
        style={{ marginBottom: 16 }}
        loading={marketQ.isLoading}
      >
        <Row gutter={[16, 16]}>
          {market.map((p: MarketPlugin) => {
            const denied = p.entitled === false;
            return (
              <Col xs={24} md={12} lg={8} key={p.id}>
                <Card
                  size="small"
                  className="af-card-hover"
                  style={{ height: "100%" }}
                  title={
                    <Space wrap>
                      <Text strong>{p.name}</Text>
                      <Tag>{p.plugin_type}</Tag>
                      {p.is_paid ? (
                        <Tag color="gold">{priceLabel(p.price_cents, true)}</Tag>
                      ) : (
                        <Tag color="green">Free</Tag>
                      )}
                      {p.installed && <Tag color="blue">Installed</Tag>}
                      {p.active && <Tag color="success">Active</Tag>}
                    </Space>
                  }
                >
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                    {p.description}
                  </Paragraph>
                  {denied && (
                    <Alert
                      type="warning"
                      showIcon
                      style={{ marginBottom: 8 }}
                      message={p.entitlement_reason || t("plugins.notEntitled")}
                    />
                  )}
                  <Can perm="system:config">
                    <Space wrap>
                      <Tooltip title={denied ? t("plugins.notEntitled") : ""}>
                        <Button
                          type="primary"
                          size="small"
                          icon={<CloudDownloadOutlined />}
                          disabled={denied || !!p.installed}
                          loading={busyId === p.id && installM.isPending}
                          onClick={() => {
                            setBusyId(p.id);
                            installM.mutate(p.id);
                          }}
                        >
                          {t("plugins.install")}
                        </Button>
                      </Tooltip>
                      <Button
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        disabled={!p.installed}
                        loading={busyId === p.id && uninstallM.isPending}
                        onClick={() => {
                          setBusyId(p.id);
                          uninstallM.mutate(p.id);
                        }}
                      >
                        {t("plugins.uninstall")}
                      </Button>
                    </Space>
                  </Can>
                </Card>
              </Col>
            );
          })}
        </Row>
      </Card>

      <Card
        title={t("plugins.installed")}
        className="af-glass"
        loading={installedQ.isLoading}
      >
        <Table
          size="small"
          rowKey="plugin_id"
          dataSource={installed}
          locale={{ emptyText: t("plugins.installedEmpty") }}
          columns={[
            { title: "ID", dataIndex: "plugin_id" },
            {
              title: t("plugins.state"),
              dataIndex: "state",
              width: 110,
              render: (s: string) => (
                <Tag color={s === "active" ? "success" : s === "error" ? "error" : "default"}>
                  {s}
                </Tag>
              ),
            },
            {
              title: "Type",
              dataIndex: "plugin_type",
              width: 120,
              render: (v: string | undefined, r) =>
                v || (r.meta as { plugin_type?: string } | null)?.plugin_type || "—",
            },
            {
              title: t("common.detail"),
              key: "actions",
              width: 220,
              render: (_, r) => (
                <Can perm="system:config">
                  <Space>
                    <Button
                      size="small"
                      icon={<ThunderboltOutlined />}
                      disabled={r.state === "active"}
                      loading={busyId === r.plugin_id && activateM.isPending}
                      onClick={() => {
                        setBusyId(r.plugin_id);
                        activateM.mutate(r.plugin_id);
                      }}
                    >
                      {t("plugins.activate")}
                    </Button>
                    <Button
                      size="small"
                      icon={<PoweroffOutlined />}
                      disabled={r.state !== "active"}
                      loading={busyId === r.plugin_id && deactivateM.isPending}
                      onClick={() => {
                        setBusyId(r.plugin_id);
                        deactivateM.mutate(r.plugin_id);
                      }}
                    >
                      {t("plugins.deactivate")}
                    </Button>
                  </Space>
                </Can>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default PluginsPage;

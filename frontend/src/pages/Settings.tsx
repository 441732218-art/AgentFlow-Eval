/* (c) 2026 AgentFlow-Eval */
/* Settings — modern SaaS identity + preferences */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Card,
  Form,
  Input,
  Switch,
  Button,
  Typography,
  Space,
  Descriptions,
  Alert,
  Tag,
  Select,
  Spin,
  Row,
  Col,
  Divider,
  theme,
  message,
  Tooltip,
} from "antd";
import {
  SaveOutlined,
  ReloadOutlined,
  UserOutlined,
  SafetyCertificateOutlined,
  KeyOutlined,
  ApiOutlined,
  CheckCircleFilled,
  CopyOutlined,
  EyeInvisibleOutlined,
  EyeOutlined,
  ThunderboltOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { settingsApi, type ActorInfo } from "@/api";
import { THEME_OPTIONS, useThemeStore } from "@/stores/useThemeStore";
import { useI18nStore, type Locale } from "@/i18n";

const { Title, Text, Paragraph } = Typography;

const STORAGE_KEY = "agentflow_settings";

interface LocalSettings {
  apiBaseUrl: string;
  apiKey: string;
  pollIntervalSec: number;
  showArchived: boolean;
  preferredActorLabel: string;
}

const defaults: LocalSettings = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  apiKey: "",
  pollIntervalSec: 3,
  showArchived: false,
  preferredActorLabel: "",
};

function loadSettings(): LocalSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...defaults };
    return { ...defaults, ...JSON.parse(raw) };
  } catch {
    return { ...defaults };
  }
}

function maskKey(key: string): string {
  if (!key) return "未配置";
  if (key.length <= 8) return "••••••••";
  return `${key.slice(0, 4)}••••${key.slice(-4)}`;
}

export default function Settings() {
  const { token } = theme.useToken();
  const { mode, setMode } = useThemeStore();
  const locale = useI18nStore((s) => s.locale);
  const setLocale = useI18nStore((s) => s.setLocale);
  const t = useI18nStore((s) => s.t);
  const [form] = Form.useForm<LocalSettings>();
  const [saved, setSaved] = useState<LocalSettings>(loadSettings);
  const [actorInfo, setActorInfo] = useState<ActorInfo | null>(null);
  const [actorLoading, setActorLoading] = useState(false);
  const [actorError, setActorError] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);

  const fetchActor = useCallback(async () => {
    setActorLoading(true);
    setActorError(null);
    try {
      const data = await settingsApi.getActor();
      setActorInfo(data);
    } catch (err: any) {
      const msg =
        err?.response?.data?.error?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        "无法获取当前身份";
      setActorError(typeof msg === "string" ? msg : "无法获取当前身份");
      setActorInfo(null);
    } finally {
      setActorLoading(false);
    }
  }, []);

  useEffect(() => {
    form.setFieldsValue(saved);
  }, [form, saved]);

  useEffect(() => {
    fetchActor();
  }, [fetchActor, saved.apiKey]);

  const onSave = async () => {
    try {
      setSaving(true);
      const values = await form.validateFields();
      const next: LocalSettings = {
        apiBaseUrl: values.apiBaseUrl?.trim() || defaults.apiBaseUrl,
        apiKey: (values.apiKey || "").trim(),
        pollIntervalSec: Number(values.pollIntervalSec) || 3,
        showArchived: !!values.showArchived,
        preferredActorLabel: (values.preferredActorLabel || "").trim(),
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setSaved(next);
      message.success("设置已保存，正在刷新身份…");
      setTimeout(() => fetchActor(), 80);
    } finally {
      setSaving(false);
    }
  };

  const onReset = () => {
    localStorage.removeItem(STORAGE_KEY);
    setSaved({ ...defaults });
    form.setFieldsValue(defaults);
    message.info("已恢复默认设置");
    setTimeout(() => fetchActor(), 80);
  };

  const copyActor = async () => {
    const a = actorInfo?.current_actor || "anonymous";
    try {
      await navigator.clipboard.writeText(a);
      message.success("Actor 已复制");
    } catch {
      message.error("复制失败");
    }
  };

  const displayActor = actorInfo?.current_actor || "anonymous";
  const isAdmin = !!actorInfo?.is_admin;

  const actorOptions = useMemo(
    () =>
      (actorInfo?.available_actors || []).map((a) => ({
        value: a,
        label: (
          <Space>
            <Tag color={(actorInfo?.admin_actors || []).includes(a) ? "gold" : "blue"}>{a}</Tag>
            {(actorInfo?.admin_actors || []).includes(a) && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                admin
              </Text>
            )}
          </Space>
        ),
      })),
    [actorInfo]
  );

  return (
    <div className="af-page">
      {/* Hero */}
      <div
        style={{
          marginBottom: 24,
          padding: "22px 24px",
          borderRadius: 16,
          border: "1px solid var(--af-border)",
          background: "var(--af-gradient-soft)",
          boxShadow: "var(--af-shadow-sm)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            right: -40,
            top: -40,
            width: 180,
            height: 180,
            borderRadius: "50%",
            background: "var(--af-gradient)",
            opacity: 0.12,
            filter: "blur(8px)",
          }}
        />
        <Space align="start" size={14}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 14,
              background: "var(--af-gradient)",
              display: "grid",
              placeItems: "center",
              color: "#fff",
              boxShadow: "var(--af-shadow-glow)",
            }}
          >
            <SettingOutlined style={{ fontSize: 22 }} />
          </div>
          <div>
            <Title level={3} style={{ margin: 0, letterSpacing: "-0.02em" }}>
              设置中心
            </Title>
            <Paragraph type="secondary" style={{ margin: "6px 0 0", maxWidth: 560 }}>
              管理 API Key、当前身份与工作区偏好。敏感密钥仅存本机浏览器，不会上传到前端代码仓库。
            </Paragraph>
          </div>
        </Space>
      </div>

      <Row gutter={[20, 20]}>
        {/* Left: Identity */}
        <Col xs={24} lg={10}>
          <Card
            className="af-card-hover af-glass"
            styles={{ body: { padding: 22 } }}
            style={{ height: "100%" }}
            title={
              <Space>
                <UserOutlined style={{ color: "var(--af-primary)" }} />
                <span>当前身份</span>
              </Space>
            }
            extra={
              <Button
                size="small"
                type="text"
                icon={<ReloadOutlined spin={actorLoading} />}
                onClick={fetchActor}
              >
                刷新
              </Button>
            }
          >
            {actorLoading && !actorInfo ? (
              <div style={{ padding: 24 }}>
                <Spin style={{ display: "block", margin: "24px auto" }} />
                <Text type="secondary" style={{ display: "block", textAlign: "center" }}>
                  正在同步身份…
                </Text>
              </div>
            ) : actorError ? (
              <Alert type="warning" showIcon message="身份服务不可用" description={actorError} />
            ) : (
              <>
                <div
                  style={{
                    padding: 20,
                    borderRadius: 14,
                    background: "var(--af-bg-muted)",
                    border: "1px solid var(--af-border)",
                    marginBottom: 16,
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      width: 72,
                      height: 72,
                      margin: "0 auto 12px",
                      borderRadius: 20,
                      background: isAdmin ? "linear-gradient(135deg,#f59e0b,#fbbf24)" : "var(--af-gradient)",
                      display: "grid",
                      placeItems: "center",
                      color: "#fff",
                      fontSize: 28,
                      fontWeight: 800,
                      boxShadow: "var(--af-shadow-glow)",
                    }}
                  >
                    {(displayActor || "A").slice(0, 1).toUpperCase()}
                  </div>
                  <Space wrap style={{ justifyContent: "center", marginBottom: 8 }}>
                    <Tag
                      color={isAdmin ? "gold" : "processing"}
                      icon={isAdmin ? <SafetyCertificateOutlined /> : <UserOutlined />}
                      style={{
                        fontSize: 14,
                        padding: "4px 12px",
                        borderRadius: 8,
                        lineHeight: "22px",
                      }}
                    >
                      {displayActor}
                    </Tag>
                    {isAdmin ? (
                      <Tag color="gold" icon={<CheckCircleFilled />}>
                        Admin
                      </Tag>
                    ) : (
                      <Tag>Standard</Tag>
                    )}
                    <span className="af-live-dot" title="已连接" />
                  </Space>
                  <div>
                    <Button type="link" size="small" icon={<CopyOutlined />} onClick={copyActor}>
                      复制 Actor
                    </Button>
                  </div>
                </div>

                <Descriptions
                  column={1}
                  size="small"
                  labelStyle={{ color: "var(--af-text-secondary)", width: 120 }}
                  contentStyle={{ color: "var(--af-text)" }}
                >
                  <Descriptions.Item label="Auth">
                    {actorInfo?.auth_enabled ? (
                      <Tag color="success">已启用</Tag>
                    ) : (
                      <Tag>开发模式（关闭）</Tag>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="租户隔离">
                    {actorInfo?.tenancy_enabled ? (
                      <Tag color="purple">开启</Tag>
                    ) : (
                      <Tag>关闭</Tag>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="API Key">
                    {actorInfo?.api_key_configured ? (
                      <Text code>{actorInfo.key_prefix || "已配置"}</Text>
                    ) : (
                      <Text type="secondary">未携带</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="Admin 列表">
                    {(actorInfo?.admin_actors || ["admin"]).map((a) => (
                      <Tag key={a} color="gold" style={{ marginBottom: 4 }}>
                        {a}
                      </Tag>
                    ))}
                  </Descriptions.Item>
                </Descriptions>

                {(actorInfo?.available_actors?.length || 0) > 0 && (
                  <>
                    <Divider style={{ margin: "16px 0" }} />
                    <Text type="secondary" style={{ fontSize: 12, display: "block", marginBottom: 8 }}>
                      已知 Actors（由 backend API_KEYS 映射）
                    </Text>
                    <Space wrap>
                      {actorInfo!.available_actors.map((a) => {
                        const admin = (actorInfo?.admin_actors || []).includes(a);
                        const active = a === displayActor;
                        return (
                          <Tag
                            key={a}
                            color={admin ? "gold" : active ? "processing" : "default"}
                            style={{
                              cursor: "default",
                              borderWidth: active ? 1.5 : 1,
                              padding: "2px 10px",
                            }}
                          >
                            {a}
                            {active ? " · 当前" : ""}
                          </Tag>
                        );
                      })}
                    </Space>
                  </>
                )}
              </>
            )}
          </Card>
        </Col>

        {/* Right: Preferences + Key */}
        <Col xs={24} lg={14}>
          <Space direction="vertical" size={20} style={{ width: "100%" }}>
            <Card
              className="af-card-hover af-glass"
              styles={{ body: { padding: 22 } }}
              title={
                <Space>
                  <KeyOutlined style={{ color: "var(--af-accent)" }} />
                  <span>API Key 管理</span>
                </Space>
              }
            >
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 16, borderRadius: 10 }}
                message="密钥仅保存在本机 localStorage"
                description={
                  <span>
                    后端配置示例：
                    <Text code>API_KEYS=alice-secret:alice,ops-secret:admin</Text>
                    。更换 Key 后保存即可切换身份。
                  </span>
                }
              />
              <Form form={form} layout="vertical" initialValues={saved} requiredMark={false}>
                <Form.Item
                  label="API Base URL"
                  name="apiBaseUrl"
                  rules={[{ required: true, message: "请输入 API 地址" }]}
                  extra="开发环境可用 /api/v1（走 Vite 代理）"
                >
                  <Input
                    prefix={<ApiOutlined style={{ color: "var(--af-text-muted)" }} />}
                    placeholder="/api/v1"
                    size="large"
                  />
                </Form.Item>

                <Form.Item
                  label="API Key"
                  name="apiKey"
                  extra={
                    <Space size={4} style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        当前：{maskKey(form.getFieldValue("apiKey") || saved.apiKey)}
                      </Text>
                    </Space>
                  }
                >
                  <Input.Password
                    size="large"
                    prefix={<KeyOutlined style={{ color: "var(--af-text-muted)" }} />}
                    placeholder="sk-… 或自定义 secret"
                    visibilityToggle={{
                      visible: showKey,
                      onVisibleChange: setShowKey,
                    }}
                    iconRender={(visible) =>
                      visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
                    }
                    autoComplete="off"
                  />
                </Form.Item>

                <Form.Item
                  label="身份备注标签（可选）"
                  name="preferredActorLabel"
                  extra="仅本地备注；真实 actor 始终由 API Key 映射决定"
                >
                  <Select
                    allowClear
                    size="large"
                    placeholder="从已知 actors 选择备注"
                    options={actorOptions}
                    optionLabelProp="value"
                  />
                </Form.Item>
              </Form>
            </Card>

            <Card
              className="af-card-hover af-glass"
              styles={{ body: { padding: 22 } }}
              title={
                <Space>
                  <ThunderboltOutlined style={{ color: "var(--af-primary)" }} />
                  <span>工作区偏好</span>
                </Space>
              }
            >
              <Form form={form} layout="vertical" requiredMark={false}>
                <Row gutter={16}>
                  <Col xs={24} sm={12}>
                    <Form.Item label="界面主题">
                      <Select
                        size="large"
                        value={mode}
                        onChange={(v) => setMode(v)}
                        optionLabelProp="label"
                        options={THEME_OPTIONS.map((opt) => ({
                          value: opt.value,
                          label: (
                            <Space size={8}>
                              <span
                                style={{
                                  width: 12,
                                  height: 12,
                                  borderRadius: "50%",
                                  background: opt.swatch,
                                  display: "inline-block",
                                  boxShadow: `0 0 0 2px ${opt.swatch}33`,
                                  flexShrink: 0,
                                }}
                              />
                              <span>{opt.label}</span>
                            </Space>
                          ),
                        }))}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item label={t("settings.language")}>
                      <Select
                        size="large"
                        value={locale}
                        onChange={(v) => setLocale(v as Locale)}
                        options={[
                          { value: "zh", label: t("settings.lang.zh") },
                          { value: "en", label: t("settings.lang.en") },
                        ]}
                      />
                    </Form.Item>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Form.Item
                      label="任务轮询间隔（秒）"
                      name="pollIntervalSec"
                      extra="用于活动通知实时刷新（1–60 秒）"
                      rules={[
                        {
                          type: "number",
                          min: 1,
                          max: 60,
                          transform: (v) => Number(v),
                        },
                      ]}
                    >
                      <Input type="number" min={1} max={60} size="large" />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item
                  label="默认显示已归档任务"
                  name="showArchived"
                  valuePropName="checked"
                  style={{ marginBottom: 8 }}
                >
                  <Switch checkedChildren="显示" unCheckedChildren="隐藏" />
                </Form.Item>
              </Form>

              <Divider style={{ margin: "12px 0 20px" }} />

              <Space wrap>
                <Button
                  type="primary"
                  size="large"
                  icon={<SaveOutlined />}
                  loading={saving}
                  onClick={onSave}
                  style={{
                    background: "var(--af-gradient)",
                    border: "none",
                    minWidth: 120,
                  }}
                >
                  保存设置
                </Button>
                <Button size="large" icon={<ReloadOutlined />} onClick={onReset}>
                  恢复默认
                </Button>
                <Tooltip title="重新向后端请求当前 actor">
                  <Button size="large" onClick={fetchActor} loading={actorLoading}>
                    校验身份
                  </Button>
                </Tooltip>
              </Space>
            </Card>

            <Card
              className="af-glass"
              size="small"
              styles={{ body: { padding: 16 } }}
              style={{ borderStyle: "dashed" }}
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="前端版本">0.1.0</Descriptions.Item>
                <Descriptions.Item label="构建模式">{import.meta.env.MODE}</Descriptions.Item>
                <Descriptions.Item label="主题 token">
                  <Text code style={{ fontSize: 12 }}>
                    primary={token.colorPrimary}
                  </Text>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Space>
        </Col>
      </Row>
    </div>
  );
}

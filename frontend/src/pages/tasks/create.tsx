/* Create task — SaaS form with OpenAI / HTTP runner support (Phase 1) */

import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Input,
  Select,
  Slider,
  InputNumber,
  Button,
  Typography,
  Row,
  Col,
  Space,
  message,
  Alert,
  Tag,
  Steps,
  Divider,
  Switch,
} from "antd";
import {
  PlusOutlined,
  CodeOutlined,
  ClearOutlined,
  ArrowLeftOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  ApiOutlined,
  CloudServerOutlined,
} from "@ant-design/icons";
import {
  taskCreateSchema,
  type TaskCreateInput,
  buildAgentConfigFromForm,
} from "@/lib/validators";
import { useCreateTask } from "@/hooks";
import { useCallback, useMemo, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useI18nStore } from "@/i18n";
import { agentsHttpApi } from "@/api/endpoints/agentsHttp";
import { DEFAULT_SCORECARD } from "@/api/endpoints/judges";

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const MODEL_OPTIONS = [
  { value: "gpt-4o", label: "GPT-4o", hint: "高质量通用" },
  { value: "gpt-4o-mini", label: "GPT-4o-mini", hint: "性价比首选" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo", hint: "长上下文" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo", hint: "快速试跑" },
  { value: "claude-3-opus", label: "Claude 3 Opus", hint: "复杂推理" },
  { value: "claude-3-sonnet", label: "Claude 3 Sonnet", hint: "均衡表现" },
];

const RUNNER_OPTIONS = [
  { value: "openai", label: "OpenAI / ReAct（内置）", icon: <ThunderboltOutlined /> },
  { value: "http", label: "HTTP Agent（外部接入）", icon: <CloudServerOutlined /> },
];

function tempLabel(t: number) {
  if (t <= 0.2) return "确定性强";
  if (t <= 0.7) return "平衡";
  if (t <= 1.2) return "有创意";
  return "高随机";
}

export default function CreateTaskPage() {
  const navigate = useNavigate();
  const t = useI18nStore((s) => s.t);
  const createTask = useCreateTask();
  const [probing, setProbing] = useState(false);
  const [probeHint, setProbeHint] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TaskCreateInput>({
    resolver: zodResolver(taskCreateSchema),
    defaultValues: {
      name: "",
      description: "",
      runner: "openai",
      model: "gpt-4o",
      temperature: 0,
      max_tokens: 4096,
      endpoint_url: "",
      timeout_sec: 60,
      headers_json: "",
      verify_ssl: true,
      scorecard_json: JSON.stringify(DEFAULT_SCORECARD, null, 2),
    },
  });

  const formValues = watch();
  const runner = formValues.runner || "openai";
  const nameOk = Boolean(formValues.name?.trim());
  const step = nameOk ? 1 : 0;

  const payloadPreview = useMemo(() => {
    return JSON.stringify(
      {
        name: formValues.name || "",
        description: formValues.description || "",
        agent_config: buildAgentConfigFromForm({
          ...formValues,
          name: formValues.name || "preview",
        } as TaskCreateInput),
      },
      null,
      2
    );
  }, [formValues]);

  const fillSample = useCallback(() => {
    reset({
      name: "Customer Support Agent Evaluation",
      description:
        "Evaluate the performance of a customer support agent on common business queries including weather, calculations, booking, and email.",
      runner: "openai",
      model: "gpt-4o-mini",
      temperature: 0,
      max_tokens: 4096,
      endpoint_url: "",
      timeout_sec: 60,
      headers_json: "",
      verify_ssl: true,
      scorecard_json: JSON.stringify(DEFAULT_SCORECARD, null, 2),
    });
  }, [reset]);

  const onProbe = useCallback(async () => {
    const url = (formValues.endpoint_url || "").trim();
    if (!url) {
      message.warning("请先填写 Endpoint URL");
      return;
    }
    let headers: Record<string, string> = {};
    if (formValues.headers_json?.trim()) {
      try {
        headers = JSON.parse(formValues.headers_json);
      } catch {
        message.error("Headers JSON 不合法");
        return;
      }
    }
    setProbing(true);
    setProbeHint(null);
    try {
      const res = await agentsHttpApi.probe({
        endpoint_url: url,
        timeout_sec: formValues.timeout_sec ?? 60,
        headers,
        verify_ssl: formValues.verify_ssl ?? true,
        query: "ping",
      });
      if (res.ssrf_blocked) {
        setProbeHint(`SSRF 拦截：${res.error || "地址不允许"}`);
        message.error(res.error || "SSRF 拦截");
      } else if (res.ok) {
        setProbeHint(
          `探测成功 · 延迟 ${res.latency_ms ?? "?"}ms · 答案预览：${res.final_answer_preview || "(空)"}`
        );
        message.success("HTTP Agent 探测成功");
      } else if (res.reachable) {
        setProbeHint(`可达但协议不完整：${res.error || res.normalized_status}`);
        message.warning(res.error || "协议兼容性不足");
      } else {
        setProbeHint(`不可达：${res.error || "网络错误"}`);
        message.error(res.error || "探测失败");
      }
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err?.message || "探测请求失败";
      setProbeHint(msg);
      message.error(msg);
    } finally {
      setProbing(false);
    }
  }, [formValues]);

  const onSubmit = handleSubmit(async (data) => {
    try {
      const agent_config = buildAgentConfigFromForm(data);
      const result = await createTask.mutateAsync({
        name: data.name,
        description: data.description || "",
        agent_config,
      });
      message.success("任务创建成功");
      navigate(`/tasks/${result.id}`);
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err?.message || "创建失败";
      message.error(msg);
    }
  });

  return (
    <form onSubmit={onSubmit} className="ic-page af-page">
      <PageHeader
        title={t("create.title")}
        subtitle={t("create.subtitle")}
        icon={<ExperimentOutlined />}
        extra={
          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tasks")}>
              {t("create.back")}
            </Button>
            <Button icon={<ClearOutlined />} onClick={fillSample}>
              {t("create.sample")}
            </Button>
          </Space>
        }
      />

      <Card className="af-glass" styles={{ body: { padding: "16px 20px" } }} style={{ marginBottom: 16 }}>
        <Steps
          size="small"
          current={step}
          items={[
            { title: "基本信息", description: "名称与描述" },
            { title: "Agent 配置", description: "OpenAI 或 HTTP" },
            { title: "创建", description: "提交并进入详情" },
          ]}
        />
      </Card>

      <Row gutter={[20, 20]}>
        <Col xs={24} lg={14}>
          <Card
            className="af-glass"
            title={
              <Space>
                <ThunderboltOutlined style={{ color: "var(--af-primary)" }} />
                <span>基本信息</span>
              </Space>
            }
          >
            <div style={{ marginBottom: 16 }}>
              <Text strong>
                任务名称 <Text type="danger">*</Text>
              </Text>
              <Controller
                name="name"
                control={control}
                render={({ field }) => (
                  <Input
                    {...field}
                    value={field.value ?? ""}
                    placeholder="例如：客服 Agent 业务评测"
                    status={errors.name ? "error" : undefined}
                    maxLength={100}
                    showCount
                    size="large"
                    style={{ marginTop: 6 }}
                  />
                )}
              />
              {errors.name && (
                <Text type="danger" style={{ fontSize: 12 }}>
                  {errors.name.message === "Task name is required"
                    ? "任务名称是必需的"
                    : errors.name.message}
                </Text>
              )}
            </div>

            <div style={{ marginBottom: 8 }}>
              <Text strong>描述</Text>
              <Controller
                name="description"
                control={control}
                render={({ field }) => (
                  <TextArea
                    {...field}
                    value={field.value ?? ""}
                    rows={3}
                    placeholder="可选：评测目标、业务场景、关注指标等"
                    style={{ marginTop: 6 }}
                  />
                )}
              />
            </div>
          </Card>

          <Card
            className="af-glass"
            style={{ marginTop: 16 }}
            title={
              <Space>
                <span>Agent 配置</span>
                <Tag color={runner === "http" ? "purple" : "blue"}>
                  {runner === "http" ? "HTTP" : formValues.model}
                </Tag>
              </Space>
            }
          >
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: "block", marginBottom: 8 }}>
                Runner 类型
              </Text>
              <Select
                value={runner}
                onChange={(val) =>
                  setValue("runner", val as "openai" | "http", { shouldValidate: true })
                }
                style={{ width: "100%" }}
                size="large"
                options={RUNNER_OPTIONS.map((o) => ({
                  value: o.value,
                  label: o.label,
                }))}
              />
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
                HTTP Runner 调用你自己托管的 Agent 接口（协议 agentflow.http.v1），评测与 Trace
                仍由平台完成。
              </Paragraph>
            </div>

            {runner === "openai" ? (
              <>
                <div style={{ marginBottom: 20 }}>
                  <Text strong style={{ display: "block", marginBottom: 8 }}>
                    模型
                  </Text>
                  <Select
                    value={formValues.model}
                    onChange={(val) => setValue("model", val, { shouldValidate: true })}
                    style={{ width: "100%" }}
                    size="large"
                    optionLabelProp="label"
                    options={MODEL_OPTIONS.map((m) => ({
                      value: m.value,
                      label: m.label,
                      m,
                    }))}
                    optionRender={(opt) => {
                      const m = (opt.data as { m: (typeof MODEL_OPTIONS)[0] }).m;
                      return (
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 12,
                          }}
                        >
                          <span>{m.label}</span>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {m.hint}
                          </Text>
                        </div>
                      );
                    }}
                  />
                </div>

                <div style={{ marginBottom: 20 }}>
                  <div
                    style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}
                  >
                    <Text strong>
                      Temperature: {(formValues.temperature ?? 0).toFixed(1)}
                    </Text>
                    <Tag>{tempLabel(formValues.temperature ?? 0)}</Tag>
                  </div>
                  <Slider
                    min={0}
                    max={2}
                    step={0.1}
                    value={formValues.temperature ?? 0}
                    onChange={(val) => setValue("temperature", val, { shouldValidate: true })}
                    marks={{ 0: "0", 0.5: "0.5", 1: "1.0", 1.5: "1.5", 2: "2.0" }}
                  />
                  <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
                    评测场景通常建议 0–0.3，保证可复现性。
                  </Paragraph>
                </div>

                <div style={{ marginBottom: 8 }}>
                  <Text strong style={{ display: "block", marginBottom: 6 }}>
                    Max Tokens
                  </Text>
                  <InputNumber
                    value={formValues.max_tokens ?? 4096}
                    onChange={(val) =>
                      setValue("max_tokens", val ?? 4096, { shouldValidate: true })
                    }
                    min={256}
                    max={16384}
                    step={256}
                    style={{ width: "100%" }}
                    size="large"
                  />
                </div>
              </>
            ) : (
              <>
                <Alert
                  type="info"
                  showIcon
                  icon={<ApiOutlined />}
                  style={{ marginBottom: 16, borderRadius: 10 }}
                  message="外部 HTTP Agent"
                  description="禁止填写内网地址（127.0.0.1 / 10.x / 192.168.x 等）。请使用公网可达的 HTTPS 端点。"
                />
                <div style={{ marginBottom: 16 }}>
                  <Text strong>
                    Endpoint URL <Text type="danger">*</Text>
                  </Text>
                  <Controller
                    name="endpoint_url"
                    control={control}
                    render={({ field }) => (
                      <Input
                        {...field}
                        value={field.value ?? ""}
                        placeholder="https://agent.example.com/v1/invoke"
                        status={errors.endpoint_url ? "error" : undefined}
                        size="large"
                        style={{ marginTop: 6 }}
                      />
                    )}
                  />
                  {errors.endpoint_url && (
                    <Text type="danger" style={{ fontSize: 12 }}>
                      {errors.endpoint_url.message}
                    </Text>
                  )}
                </div>

                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ display: "block", marginBottom: 6 }}>
                    Timeout（秒）
                  </Text>
                  <InputNumber
                    value={formValues.timeout_sec ?? 60}
                    onChange={(val) =>
                      setValue("timeout_sec", val ?? 60, { shouldValidate: true })
                    }
                    min={1}
                    max={300}
                    style={{ width: "100%" }}
                    size="large"
                  />
                </div>

                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ display: "block", marginBottom: 6 }}>
                    Headers（JSON 对象，可选）
                  </Text>
                  <Controller
                    name="headers_json"
                    control={control}
                    render={({ field }) => (
                      <TextArea
                        {...field}
                        value={field.value ?? ""}
                        rows={3}
                        placeholder='{"Authorization":"Bearer sk-..."}'
                        status={errors.headers_json ? "error" : undefined}
                      />
                    )}
                  />
                  {errors.headers_json && (
                    <Text type="danger" style={{ fontSize: 12 }}>
                      {errors.headers_json.message}
                    </Text>
                  )}
                </div>

                <div
                  style={{
                    marginBottom: 16,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <Text strong>校验 TLS 证书</Text>
                  <Switch
                    checked={formValues.verify_ssl ?? true}
                    onChange={(v) => setValue("verify_ssl", v)}
                  />
                </div>

                <Space wrap>
                  <Button loading={probing} onClick={onProbe} icon={<ApiOutlined />}>
                    探测 Agent（Probe）
                  </Button>
                </Space>
                {probeHint && (
                  <Alert
                    style={{ marginTop: 12, borderRadius: 10, fontSize: 12 }}
                    type={probeHint.includes("成功") ? "success" : "warning"}
                    showIcon
                    message={probeHint}
                  />
                )}
              </>
            )}
          </Card>

          <Card
            className="af-glass"
            style={{ marginTop: 16 }}
            title="Judge 评分卡（可选）"
          >
            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              默认 40/40/20 三维评分。可编辑 dimensions 的 weight（会归一到 100）与 description。
              写入 <Text code>agent_config.scorecard</Text>，评测流水线会真正使用这些权重。
            </Paragraph>
            <Controller
              name="scorecard_json"
              control={control}
              render={({ field }) => (
                <TextArea
                  {...field}
                  value={field.value ?? ""}
                  rows={10}
                  status={errors.scorecard_json ? "error" : undefined}
                  style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}
                />
              )}
            />
            {errors.scorecard_json && (
              <Text type="danger" style={{ fontSize: 12 }}>
                {errors.scorecard_json.message}
              </Text>
            )}
            <Button
              size="small"
              style={{ marginTop: 8 }}
              onClick={() =>
                setValue(
                  "scorecard_json",
                  JSON.stringify(DEFAULT_SCORECARD, null, 2),
                  { shouldValidate: true }
                )
              }
            >
              恢复默认评分卡
            </Button>
          </Card>

          <div className="af-form-actions af-no-print">
            <Space wrap>
              <Button
                type="primary"
                htmlType="submit"
                icon={<PlusOutlined />}
                size="large"
                loading={createTask.isPending || isSubmitting}
                style={{ background: "var(--af-gradient)", border: "none" }}
              >
                {t("create.submit")}
              </Button>
              <Button size="large" onClick={() => navigate("/tasks")}>
                {t("create.cancel")}
              </Button>
            </Space>
          </div>
        </Col>

        <Col xs={24} lg={10}>
          <Card
            className="af-glass af-sticky-preview"
            title={
              <Space>
                <CodeOutlined />
                <span>请求预览</span>
              </Space>
            }
            extra={
              <Tag color="processing" style={{ margin: 0 }}>
                Live
              </Tag>
            }
          >
            <pre className="af-code-block">{payloadPreview}</pre>
            <Divider style={{ margin: "12px 0" }} />
            <Space direction="vertical" size={6} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <Text type="secondary">Runner</Text>
                <Text>{runner}</Text>
              </div>
              {runner === "openai" ? (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">模型</Text>
                    <Text>{formValues.model}</Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">Temperature</Text>
                    <Text>{(formValues.temperature ?? 0).toFixed(1)}</Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">Max Tokens</Text>
                    <Text>{formValues.max_tokens ?? 4096}</Text>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">Endpoint</Text>
                    <Text ellipsis style={{ maxWidth: 180 }}>
                      {formValues.endpoint_url || "—"}
                    </Text>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <Text type="secondary">Timeout</Text>
                    <Text>{formValues.timeout_sec ?? 60}s</Text>
                  </div>
                </>
              )}
            </Space>
            <Alert
              message="右侧预览即为实际提交的 JSON 载荷（agent_config）。"
              type="info"
              showIcon
              style={{ marginTop: 14, fontSize: 12, borderRadius: 10 }}
            />
          </Card>
        </Col>
      </Row>
    </form>
  );
}

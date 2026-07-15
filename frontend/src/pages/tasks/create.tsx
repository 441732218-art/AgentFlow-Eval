/* Create task — SaaS form with live payload preview */

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
} from "antd";
import {
  PlusOutlined,
  CodeOutlined,
  ClearOutlined,
  ArrowLeftOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { taskCreateSchema, type TaskCreateInput } from "@/lib/validators";
import { useCreateTask } from "@/hooks";
import { useCallback, useMemo } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { useI18nStore } from "@/i18n";

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
      model: "gpt-4o",
      temperature: 0,
      max_tokens: 4096,
    },
  });

  const formValues = watch();
  const nameOk = Boolean(formValues.name?.trim());
  const step = nameOk ? 1 : 0;

  const payloadPreview = useMemo(() => {
    return JSON.stringify(
      {
        name: formValues.name || "",
        description: formValues.description || "",
        agent_config: {
          model: formValues.model || "gpt-4o",
          temperature: formValues.temperature ?? 0,
          max_tokens: formValues.max_tokens ?? 4096,
        },
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
      model: "gpt-4o-mini",
      temperature: 0,
      max_tokens: 4096,
    });
  }, [reset]);

  const onSubmit = handleSubmit(async (data) => {
    try {
      const result = await createTask.mutateAsync({
        name: data.name,
        description: data.description || "",
        agent_config: {
          model: data.model || "gpt-4o",
          temperature: data.temperature ?? 0,
          max_tokens: data.max_tokens ?? 4096,
        },
      });
      message.success("任务创建成功");
      navigate(`/tasks/${result.id}`);
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err?.message || "创建失败";
      message.error(msg);
    }
  });

  return (
    <form onSubmit={onSubmit} className="af-page">
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
            { title: "模型参数", description: "Agent 配置" },
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
              {/* Ant Design Input 必须用 Controller，不能用 register，否则输入不会写入表单状态 */}
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
                <Tag color="blue">{formValues.model}</Tag>
              </Space>
            }
          >
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
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
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
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
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
            </Space>
            <Alert
              message="右侧预览即为实际提交的 JSON 载荷。"
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

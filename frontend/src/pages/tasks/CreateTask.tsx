import { useForm } from "react-hook-form";
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
} from "antd";
import {
  PlusOutlined,
  CodeOutlined,
  ClearOutlined,
} from "@ant-design/icons";
import { taskCreateSchema, type TaskCreateInput } from "@/lib/validators";
import { useCreateTask } from "@/hooks";
import { useCallback, useMemo } from "react";

const { TextArea } = Input;
const { Text } = Typography;

const MODEL_OPTIONS = [
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o-mini" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
  { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
  { value: "claude-3-opus", label: "Claude 3 Opus" },
  { value: "claude-3-sonnet", label: "Claude 3 Sonnet" },
];

export default function CreateTaskPage() {
  const navigate = useNavigate();
  const createTask = useCreateTask();

  const {
    register,
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
      message.success("Task created successfully");
      navigate(`/tasks/${result.id}`);
    } catch (err: any) {
      const msg = err?.response?.data?.error?.message || err?.message || "Failed to create task";
      message.error(msg);
    }
  });

  return (
    <form onSubmit={onSubmit}>
      <Row gutter={24}>
        {/* Left: Form */}
        <Col span={14}>
          <Card title="Create Evaluation Task">
            {/* Task Name */}
            <div style={{ marginBottom: 16 }}>
              <Text strong>
                Task Name <Text type="danger">*</Text>
              </Text>
              <Input
                {...register("name")}
                placeholder="e.g. Customer Support Agent Eval"
                status={errors.name ? "error" : undefined}
                maxLength={100}
                showCount
              />
              {errors.name && (
                <Text type="danger" style={{ fontSize: 12 }}>
                  {errors.name.message}
                </Text>
              )}
            </div>

            {/* Description */}
            <div style={{ marginBottom: 16 }}>
              <Text strong>Description</Text>
              <TextArea
                {...register("description")}
                rows={3}
                placeholder="Optional description of the evaluation task"
              />
            </div>

            {/* Model Selection */}
            <div style={{ marginBottom: 16 }}>
              <Text strong>Agent Model</Text>
              <Select
                value={formValues.model}
                onChange={(val) => setValue("model", val, { shouldValidate: true })}
                options={MODEL_OPTIONS}
                style={{ width: "100%" }}
              />
            </div>

            {/* Temperature */}
            <div style={{ marginBottom: 16 }}>
              <Text strong>Temperature: {formValues.temperature?.toFixed(1)}</Text>
              <Slider
                min={0}
                max={2}
                step={0.1}
                value={formValues.temperature ?? 0}
                onChange={(val) => setValue("temperature", val, { shouldValidate: true })}
                marks={{ 0: "0", 0.5: "0.5", 1: "1.0", 1.5: "1.5", 2: "2.0" }}
              />
            </div>

            {/* Max Tokens */}
            <div style={{ marginBottom: 24 }}>
              <Text strong>Max Tokens</Text>
              <InputNumber
                value={formValues.max_tokens ?? 4096}
                onChange={(val) =>
                  setValue("max_tokens", val ?? 4096, { shouldValidate: true })
                }
                min={256}
                max={16384}
                step={256}
                style={{ width: "100%" }}
              />
            </div>

            {/* Actions */}
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<PlusOutlined />}
                loading={createTask.isPending || isSubmitting}
              >
                Create Task
              </Button>
              <Button icon={<ClearOutlined />} onClick={fillSample}>
                Fill Sample
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Right: JSON Preview */}
        <Col span={10}>
          <Card
            title={
              <Space>
                <CodeOutlined />
                <span>Request Preview</span>
              </Space>
            }
          >
            <pre
              style={{
                background: "#1e1e2e",
                color: "#cdd6f4",
                padding: 16,
                borderRadius: 8,
                fontSize: 13,
                lineHeight: 1.5,
                overflow: "auto",
                maxHeight: 480,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              }}
            >
              {payloadPreview}
            </pre>
            <Alert
              message="The request preview shows the exact payload that will be sent to the API."
              type="info"
              showIcon
              style={{ marginTop: 12, fontSize: 12 }}
            />
          </Card>
        </Col>
      </Row>
    </form>
  );
}



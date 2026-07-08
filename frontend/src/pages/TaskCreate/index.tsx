/* (c) 2026 AgentFlow-Eval */
/* 创建评测任务页 */

import React from "react";
import {
  Card,
  Form,
  Input,
  InputNumber,
  Select,
  Button,
  message,
} from "antd";
import { useNavigate } from "react-router-dom";
import { useTaskStore } from "../../stores/useTaskStore";

const { TextArea } = Input;

const TaskCreate: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { createTask } = useTaskStore();

  const handleSubmit = async (values: Record<string, unknown>) => {
    try {
      const task = await createTask({
        name: values.name as string,
        description: (values.description as string) || "",
        agent_config: {
          model: values.model || "gpt-4o",
          temperature: values.temperature || 0,
          max_tokens: (values as { max_tokens?: number }).max_tokens || 4096,
        },
      });
      message.success("任务创建成功");
      navigate(`/tasks/${task.id}`);
    } catch {
      message.error("创建失败，请检查参数");
    }
  };

  return (
    <Card title="创建评测任务">
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{ model: "gpt-4o", temperature: 0, max_tokens: 4096 }}
        style={{ maxWidth: 600 }}
      >
        <Form.Item name="name" label="任务名称" rules={[{ required: true, message: "请输入任务名称" }]}>
          <Input placeholder="输入评测任务名称" />
        </Form.Item>

        <Form.Item name="description" label="任务描述">
          <TextArea rows={3} placeholder="可选的描述信息" />
        </Form.Item>

        <Form.Item name="model" label="Agent 模型">
          <Select>
            <Select.Option value="gpt-4o">GPT-4o</Select.Option>
            <Select.Option value="gpt-4o-mini">GPT-4o-mini</Select.Option>
            <Select.Option value="gpt-4-turbo">GPT-4 Turbo</Select.Option>
          </Select>
        </Form.Item>

        <Form.Item name="temperature" label="温度">
          <InputNumber min={0} max={2} step={0.1} />
        </Form.Item>

        <Form.Item name="max_tokens" label="最大 Token">
          <InputNumber min={256} max={16384} step={256} />
        </Form.Item>

        <Form.Item>
          <Button type="primary" htmlType="submit">
            创建任务
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

export default TaskCreate;

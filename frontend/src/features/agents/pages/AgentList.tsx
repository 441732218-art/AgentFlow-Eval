import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Space,
  Switch,
  Table,
  Typography,
  message,
} from "antd";
import { PlusOutlined, ReloadOutlined, RobotOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { governanceApi } from "@/api/governance";
import { runtimeApi } from "@/api/runtime";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { DecisionBadge } from "@/components/governance/DecisionBadge";
import { agentsApi } from "../api/agents";
import { AgentStatus } from "../components/AgentStatus";
import { ExecutionStatusTag } from "../components/ExecutionStatusTag";
import type { AgentCreatePayload, AgentFleetRow } from "../types/agent";

const { Text, Paragraph } = Typography;

function buildFleetRows(
  agents: AgentFleetRow[],
  qualityGates: Awaited<ReturnType<typeof governanceApi.listQualityGates>>,
  executions: Awaited<ReturnType<typeof runtimeApi.listExecutions>>,
): AgentFleetRow[] {
  const gateByAgent = new Map(qualityGates.items.map((item) => [item.agent_id, item]));
  const lastExecutionByAgent = new Map<string, (typeof executions.items)[number]>();
  for (const item of executions.items ?? []) {
    if (!item.agent_id || lastExecutionByAgent.has(item.agent_id)) continue;
    lastExecutionByAgent.set(item.agent_id, item);
  }

  return agents.map((agent) => {
    const gate = gateByAgent.get(agent.id);
    const lastExecution = lastExecutionByAgent.get(agent.id);
    return {
      ...agent,
      current_active_version: gate?.current_version ?? agent.current_active_version,
      environment: gate?.deployment_status ?? (agent.current_active_version ? "production" : null),
      quality_gate: gate?.quality_gate ?? null,
      last_execution_id: lastExecution?.execution_id ?? null,
      last_execution_status: lastExecution?.status ?? null,
      last_execution_at: lastExecution?.started_at ?? lastExecution?.created_at ?? null,
    };
  });
}

export default function AgentList() {
  const navigate = useNavigate();
  const [fleet, setFleet] = useState<AgentFleetRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm<AgentCreatePayload & { tool_names_text?: string }>();

  const loadFleet = useCallback(async () => {
    setLoading(true);
    try {
      const [agentData, qualityGates, executions] = await Promise.all([
        agentsApi.listAgents(),
        governanceApi.listQualityGates().catch(() => ({ items: [], count: 0 })),
        runtimeApi.listExecutions({ limit: 200 }).catch(() => ({ items: [] })),
      ]);
      setFleet(buildFleetRows(agentData.agents, qualityGates, executions));
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load agent fleet");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadFleet();
  }, [loadFleet]);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      setCreating(true);
      const toolNames = (values.tool_names_text ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const created = await agentsApi.createAgent({
        id: values.id.trim(),
        name: values.name.trim(),
        description: values.description ?? "",
        tool_names: toolNames,
        system_prompt: values.system_prompt ?? "",
        enabled: values.enabled ?? true,
        roles: [],
      });
      message.success(`Agent "${created.name}" created`);
      setCreateOpen(false);
      form.resetFields();
      await loadFleet();
      navigate(`/agents/${created.id}`);
    } catch (err) {
      if (err && typeof err === "object" && "errorFields" in err) return;
      message.error(err instanceof Error ? err.message : "Failed to create agent");
    } finally {
      setCreating(false);
    }
  };

  const columns: ColumnsType<AgentFleetRow> = useMemo(
    () => [
      {
        title: "Agent Name",
        dataIndex: "name",
        key: "name",
        render: (name: string, row) => (
          <Space direction="vertical" size={0}>
            <Text strong>{name}</Text>
            <Text type="secondary" code style={{ fontSize: 12 }}>
              {row.id}
            </Text>
          </Space>
        ),
      },
      {
        title: "Status",
        key: "status",
        render: (_, row) => <AgentStatus agent={row} />,
      },
      {
        title: "Current Version",
        key: "current_version",
        render: (_, row) =>
          row.current_active_version ? (
            <Text code>{row.current_active_version}</Text>
          ) : (
            <Text type="secondary">Not deployed</Text>
          ),
      },
      {
        title: "Environment",
        dataIndex: "environment",
        key: "environment",
        render: (value?: string | null) =>
          value ? <Text code>{value}</Text> : <Text type="secondary">—</Text>,
      },
      {
        title: "Quality Gate",
        key: "quality_gate",
        render: (_, row) => <DecisionBadge decision={row.quality_gate} />,
      },
      {
        title: "Last Execution",
        key: "last_execution",
        render: (_, row) =>
          row.last_execution_id ? (
            <Space direction="vertical" size={0}>
              <ExecutionStatusTag status={row.last_execution_status ?? "UNKNOWN"} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {row.last_execution_at
                  ? new Date(row.last_execution_at).toLocaleString()
                  : row.last_execution_id}
              </Text>
            </Space>
          ) : (
            <Text type="secondary">—</Text>
          ),
      },
    ],
    [],
  );

  if (loading && fleet.length === 0) {
    return <PageSkeleton variant="cards" />;
  }

  return (
    <PageShell
      title="Agent Operations Console"
      subtitle="Enterprise agent fleet — configure, deploy, observe, and govern"
      icon={<RobotOutlined />}
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadFleet()}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            Create Agent
          </Button>
        </Space>
      }
    >
      {fleet.length === 0 && !loading ? (
        <EmptyState
          title="No agents in your fleet"
          description="Create an agent to start the configure → publish → deploy → execute lifecycle."
          actionLabel="Create Agent"
          onAction={() => setCreateOpen(true)}
        />
      ) : (
        <Card className="ic-panel">
          <Table
            rowKey="id"
            loading={loading}
            columns={columns}
            dataSource={fleet}
            onRow={(record) => ({
              onClick: () => navigate(`/agents/${record.id}`),
              style: { cursor: "pointer" },
            })}
            pagination={{ pageSize: 20, showSizeChanger: true }}
          />
        </Card>
      )}

      <Modal
        title="Create Agent"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => void handleCreate()}
        confirmLoading={creating}
        width={640}
        destroyOnClose
      >
        <Paragraph type="secondary">
          Creates a draft agent. Publish a version and deploy to production before executing.
        </Paragraph>
        <Form form={form} layout="vertical" initialValues={{ enabled: true }}>
          <Form.Item
            name="id"
            label="Agent ID"
            rules={[
              { required: true, message: "Agent ID is required" },
              { pattern: /^[\w.-]+$/, message: "Use letters, numbers, dots, dashes, underscores" },
            ]}
          >
            <Input placeholder="demo.support_agent" />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="Support Agent" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="tool_names_text"
            label="Tools (comma-separated)"
            extra="Demo: trade.search_customer — must match a registered capability tool."
          >
            <Input placeholder="trade.search_customer" />
          </Form.Item>
          <Form.Item name="system_prompt" label="System Prompt">
            <Input.TextArea rows={4} placeholder="You are a helpful support agent..." />
          </Form.Item>
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </PageShell>
  );
}

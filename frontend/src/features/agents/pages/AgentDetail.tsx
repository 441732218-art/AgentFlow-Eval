import { useCallback, useEffect, useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { Button, Card, Descriptions, Form, Input, Space, Switch, Tabs, Tag, message } from "antd";
import { ArrowLeftOutlined, RobotOutlined, SaveOutlined } from "@ant-design/icons";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { agentsApi } from "../api/agents";
import { AgentStatus } from "../components/AgentStatus";
import { RecentExecutions } from "../components/RecentExecutions";
import type { AgentDetail as AgentDetailType, AgentUpdatePayload } from "../types/agent";

const TAB_KEYS = [
  "overview",
  "versions",
  "deployments",
  "executions",
  "trace",
  "evaluations",
  "governance",
] as const;

export function AgentOverviewPanel({
  agent,
  onSaved,
}: {
  agent: AgentDetailType;
  onSaved: () => void;
}) {
  const [form] = Form.useForm<AgentUpdatePayload & { tool_names_text?: string }>();
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    form.setFieldsValue({
      name: agent.name,
      description: agent.description,
      system_prompt: agent.system_prompt,
      enabled: agent.enabled,
      tool_names_text: agent.tool_names.join(", "),
    });
  }, [agent, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const toolNames = (values.tool_names_text ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await agentsApi.updateAgent(agent.id, {
        name: values.name,
        description: values.description ?? "",
        system_prompt: values.system_prompt ?? "",
        enabled: values.enabled ?? true,
        tool_names: toolNames,
        roles: agent.roles,
        model_config: agent.model_config,
      });
      message.success("Draft updated");
      onSaved();
    } catch (err) {
      if (err && typeof err === "object" && "errorFields" in err) return;
      message.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Card title="Overview" className="ic-panel">
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="Agent ID">
            <Tag>{agent.id}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            <AgentStatus agent={agent} />
          </Descriptions.Item>
          <Descriptions.Item label="Draft Version">{agent.version}</Descriptions.Item>
          <Descriptions.Item label="Deployed Version">
            {agent.current_active_version ? (
              <Tag color="blue">{agent.current_active_version}</Tag>
            ) : (
              "—"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Roles">
            {agent.roles.length ? agent.roles.map((r) => <Tag key={r}>{r}</Tag>) : "—"}
          </Descriptions.Item>
          <Descriptions.Item label="Model Config">
            <pre style={{ margin: 0, fontSize: 12 }}>
              {JSON.stringify(agent.model_config ?? {}, null, 2)}
            </pre>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <RecentExecutions agentId={agent.id} limit={20} />

      <Card
        title="Configure Draft"
        className="ic-panel"
        extra={
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={() => void handleSave()}>
            Save Draft
          </Button>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="tool_names_text" label="Tools (comma-separated)">
            <Input />
          </Form.Item>
          <Form.Item name="system_prompt" label="System Prompt">
            <Input.TextArea rows={6} />
          </Form.Item>
          <Form.Item name="enabled" label="Enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
}

export default function AgentDetailLayout() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const [agent, setAgent] = useState<AgentDetailType | null>(null);
  const [loading, setLoading] = useState(true);

  const activeTab = useMemo(() => {
    const parts = location.pathname.split("/").filter(Boolean);
    const tabSegment = parts.length > 2 ? parts[2] : "overview";
    return TAB_KEYS.includes(tabSegment as (typeof TAB_KEYS)[number]) ? tabSegment : "overview";
  }, [location.pathname]);

  const loadAgent = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await agentsApi.getAgent(id);
      setAgent(data);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load agent");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void loadAgent();
  }, [loadAgent]);

  if (loading && !agent) {
    return <PageSkeleton variant="detail" />;
  }

  if (!agent) {
    return (
      <PageShell title="Agent not found">
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/agents")}>
          Back to fleet
        </Button>
      </PageShell>
    );
  }

  const tabItems = [
    { key: "overview", label: "Overview" },
    { key: "versions", label: "Versions" },
    { key: "deployments", label: "Deployments" },
    { key: "executions", label: "Execution" },
    { key: "trace", label: "Trace" },
    { key: "evaluations", label: "Evaluation" },
    { key: "governance", label: "Governance" },
  ];

  return (
    <PageShell
      title={agent.name}
      subtitle={agent.id}
      icon={<RobotOutlined />}
      extra={
        <Space>
          <Button
            onClick={() => navigate(`/intelligence/agents/${encodeURIComponent(id)}/console`)}
          >
            Intelligence Console
          </Button>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/agents")}>
            Agent Fleet
          </Button>
        </Space>
      }
    >
      <Tabs
        activeKey={activeTab}
        onChange={(key) => navigate(`/agents/${id}/${key}${location.search}`)}
        items={tabItems}
        style={{ marginBottom: 16 }}
      />
      {activeTab === "overview" ? (
        <AgentOverviewPanel agent={agent} onSaved={() => void loadAgent()} />
      ) : (
        <Outlet context={{ agent, reloadAgent: loadAgent }} />
      )}
    </PageShell>
  );
}

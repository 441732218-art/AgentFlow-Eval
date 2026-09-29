import { useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { Alert, Button, Card, Input, Space, Typography, message } from "antd";
import { PlayCircleOutlined, NodeIndexOutlined } from "@ant-design/icons";
import { agentsApi } from "../api/agents";
import type { AgentDetail, RuntimeExecuteResponse } from "../types/agent";

const { Paragraph, Text } = Typography;
const LAST_EXECUTION_KEY = "agentflow:last_execution";

export function saveLastExecution(agentId: string, executionId: string) {
  try {
    sessionStorage.setItem(
      LAST_EXECUTION_KEY,
      JSON.stringify({ agentId, executionId, at: Date.now() }),
    );
  } catch {
    /* ignore */
  }
}

export default function AgentExecute() {
  const navigate = useNavigate();
  const { agent } = useOutletContext<{ agent: AgentDetail }>();
  const [task, setTask] = useState("Search for customer ACME Corp and summarize account status.");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RuntimeExecuteResponse | null>(null);

  const handleExecute = async () => {
    const trimmed = task.trim();
    if (!trimmed) {
      message.warning("Enter a task");
      return;
    }
    setRunning(true);
    setResult(null);
    try {
      const response = await agentsApi.executeAgent(agent.id, trimmed);
      setResult(response);
      saveLastExecution(agent.id, response.execution_id);
      if (response.status === "SUCCESS") {
        message.success("Execution completed");
      } else {
        message.warning(response.error ?? "Execution failed");
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Execute failed");
    } finally {
      setRunning(false);
    }
  };

  const viewTrace = () => {
    if (!result?.execution_id) return;
    navigate(`/agents/${agent.id}/trace?executionId=${encodeURIComponent(result.execution_id)}`);
  };

  return (
    <Card className="ic-panel" title="Execute Test">
      <Paragraph type="secondary">
        Runs against the <Text strong>active production deployment</Text>. Ensure a version is
        published and deployed before testing.
      </Paragraph>

      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Input.TextArea
          rows={4}
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="Enter a task for the agent..."
        />
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          loading={running}
          onClick={() => void handleExecute()}
        >
          Execute
        </Button>

        {result ? (
          <Alert
            type={result.status === "SUCCESS" ? "success" : "error"}
            showIcon
            message={`Status: ${result.status}`}
            description={
              <Space direction="vertical" style={{ width: "100%" }}>
                <div>
                  <Text type="secondary">Execution ID: </Text>
                  <Text code copyable>
                    {result.execution_id}
                  </Text>
                </div>
                {result.error ? <Text type="danger">{result.error}</Text> : null}
                {result.output != null ? (
                  <pre style={{ margin: 0, fontSize: 12, maxHeight: 240, overflow: "auto" }}>
                    {JSON.stringify(result.output, null, 2)}
                  </pre>
                ) : null}
                <Button icon={<NodeIndexOutlined />} onClick={viewTrace}>
                  View Trace
                </Button>
              </Space>
            }
          />
        ) : null}
      </Space>
    </Card>
  );
}

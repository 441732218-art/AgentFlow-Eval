import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useParams, useSearchParams } from "react-router-dom";
import { Button, Card, Input, Space, Typography, message } from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { agentsApi } from "../api/agents";
import { EvidencePanel } from "../components/EvidencePanel";
import { TraceTimeline } from "../components/TraceTimeline";
import type {
  AgentDetail,
  ExecutionEvidence,
  ExecutionTraceResponse,
  TraceStep,
} from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
};

/** Normalize trace API shapes into TraceTimeline steps. */
function normalizeTraceSteps(
  data: ExecutionTraceResponse & { events?: TraceStep[] },
): TraceStep[] {
  if (Array.isArray(data.trace) && data.trace.length) {
    return data.trace.map((entry) => ({
      type: entry.event_type,
      timestamp: entry.timestamp,
      tool_name: entry.tool_name,
      status: entry.status,
      duration_ms: entry.duration_ms,
      metadata: entry.metadata,
    }));
  }
  if (Array.isArray(data.steps) && data.steps.length) {
    return data.steps;
  }
  if (Array.isArray(data.events) && data.events.length) {
    return data.events;
  }
  return [];
}

export default function AgentTrace() {
  const { agent } = useOutletContext<OutletContext>();
  const { id = "" } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [executionId, setExecutionId] = useState(
    () => searchParams.get("executionId") ?? "",
  );
  const [trace, setTrace] = useState<ExecutionTraceResponse | null>(null);
  const [evidence, setEvidence] = useState<ExecutionEvidence | null>(null);
  const [loading, setLoading] = useState(false);

  const loadTrace = useCallback(async (targetId: string) => {
    const trimmed = targetId.trim();
    if (!trimmed) {
      message.warning("Enter an execution ID");
      return;
    }
    setLoading(true);
    try {
      const [traceData, evidenceData] = await Promise.all([
        agentsApi.getExecutionTrace(trimmed),
        agentsApi.getExecutionEvidence(trimmed).catch(() => null),
      ]);
      setTrace(traceData);
      setEvidence(evidenceData);
      setSearchParams({ executionId: trimmed });
    } catch (err) {
      setTrace(null);
      setEvidence(null);
      message.error(err instanceof Error ? err.message : "Failed to load trace");
    } finally {
      setLoading(false);
    }
  }, [setSearchParams]);

  useEffect(() => {
    const fromQuery = searchParams.get("executionId");
    if (fromQuery) {
      setExecutionId(fromQuery);
      void loadTrace(fromQuery);
    }
  }, [searchParams, loadTrace]);

  useEffect(() => {
    if (searchParams.get("executionId")) return;
    try {
      const raw = sessionStorage.getItem("agentflow:last_execution");
      if (!raw) return;
      const parsed = JSON.parse(raw) as { agentId?: string; executionId?: string };
      if (parsed.agentId === (id || agent.id) && parsed.executionId) {
        setExecutionId(parsed.executionId);
      }
    } catch {
      /* ignore */
    }
  }, [id, agent.id, searchParams]);

  const steps = trace ? normalizeTraceSteps(trace as ExecutionTraceResponse & { events?: TraceStep[] }) : [];

  return (
    <Card
      className="ic-panel"
      title="Execution Trace"
      extra={
        <Button
          icon={<ReloadOutlined />}
          loading={loading}
          disabled={!executionId.trim()}
          onClick={() => void loadTrace(executionId)}
        >
          Refresh
        </Button>
      }
    >
      <Paragraph type="secondary">
        Debug timeline for agent <Text code>{agent.id}</Text>. Open from the Executions tab or enter
        an execution ID below.
      </Paragraph>

      <Space.Compact style={{ width: "100%", maxWidth: 560, marginBottom: 24 }}>
        <Input
          placeholder="execution_id"
          value={executionId}
          onChange={(e) => setExecutionId(e.target.value)}
          onPressEnter={() => void loadTrace(executionId)}
        />
        <Button
          type="primary"
          icon={<SearchOutlined />}
          loading={loading}
          onClick={() => void loadTrace(executionId)}
        >
          Load Trace
        </Button>
      </Space.Compact>

      {trace ? (
        <div>
          <EvidencePanel evidence={evidence} loading={loading} />
          <Paragraph>
            <Text type="secondary">Execution: </Text>
            <Text code>{trace.execution_id}</Text>
          </Paragraph>
          <TraceTimeline steps={steps} />
        </div>
      ) : null}
    </Card>
  );
}

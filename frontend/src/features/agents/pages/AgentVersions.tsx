import { useCallback, useEffect, useState } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { Alert, Button, Card, Typography, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { agentsApi } from "../api/agents";
import { VersionTable } from "../components/VersionTable";
import type {
  AgentDetail,
  AgentVersionRow,
  EvaluationSummary,
  VersionBenchmarkSummary,
} from "../types/agent";

const { Paragraph } = Typography;

type OutletContext = {
  agent: AgentDetail;
};

function enrichVersionRows(
  versions: AgentVersionRow[],
  evaluations: EvaluationSummary[],
  benchmarks: VersionBenchmarkSummary[],
  activeVersion?: string,
): AgentVersionRow[] {
  const evalByVersion = new Map<string, EvaluationSummary>();
  for (const item of evaluations) {
    const existing = evalByVersion.get(item.agent_version);
    if (!existing || (item.completed_at ?? "") > (existing.completed_at ?? "")) {
      evalByVersion.set(item.agent_version, item);
    }
  }

  const benchByCandidate = new Map<string, VersionBenchmarkSummary>();
  for (const item of benchmarks) {
    benchByCandidate.set(item.candidate_version, item);
  }

  return versions.map((version) => {
    const evaluation = evalByVersion.get(version.version);
    const benchmark = benchByCandidate.get(version.version);
    let benchmarkResult: string | null = null;
    if (benchmark) {
      if (benchmark.regression_detected === true) benchmarkResult = "REGRESSION";
      else if (benchmark.regression_detected === false) benchmarkResult = "STABLE";
      else benchmarkResult = benchmark.status;
    }
    return {
      ...version,
      evaluation_score: evaluation?.score ?? null,
      benchmark_result: benchmarkResult,
      deployment_status:
        version.version === activeVersion ? "ACTIVE · production" : version.deployment_status ?? null,
    };
  });
}

export default function AgentVersions() {
  const { id = "" } = useParams<{ id: string }>();
  const { agent } = useOutletContext<OutletContext>();
  const [versions, setVersions] = useState<AgentVersionRow[]>([]);
  const [loading, setLoading] = useState(true);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    try {
      const agentId = id || agent.id;
      const [versionData, evalData, benchData, deploymentData] = await Promise.all([
        agentsApi.listVersions(agentId),
        agentsApi.listEvaluations(agentId).catch(() => ({ evaluations: [], count: 0 })),
        agentsApi.listBenchmarks(agentId).catch(() => ({ benchmarks: [], count: 0 })),
        agentsApi.listDeployments(agentId).catch(() => ({ deployments: [], count: 0 })),
      ]);
      const activeDeployment = deploymentData.deployments.find(
        (item) => item.status === "ACTIVE" && item.environment === "production",
      );
      setVersions(
        enrichVersionRows(
          versionData.versions,
          evalData.evaluations,
          benchData.benchmarks,
          activeDeployment?.version ?? agent.current_active_version,
        ),
      );
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load versions");
    } finally {
      setLoading(false);
    }
  }, [id, agent.id, agent.current_active_version]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  return (
    <Card
      className="ic-panel"
      title="Version Registry"
      extra={
        <Button icon={<ReloadOutlined />} onClick={() => void loadVersions()} loading={loading}>
          Refresh
        </Button>
      }
    >
      <Alert
        type="info"
        showIcon
        message="Read-only view"
        description="Publishing and deployment actions are governed separately. Use the governance workflow to approve releases before deployment."
        style={{ marginBottom: 16 }}
      />
      <Paragraph type="secondary">
        Immutable published versions for agent <strong>{agent.name}</strong>. Evaluation scores and
        benchmark results are shown when available.
      </Paragraph>
      <VersionTable versions={versions} loading={loading} />
    </Card>
  );
}

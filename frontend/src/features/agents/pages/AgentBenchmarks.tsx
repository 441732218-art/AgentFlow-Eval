import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Button,
  Card,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  ArrowRightOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { agentsApi } from "../api/agents";
import type { AgentDetail, AgentVersion, VersionBenchmarkSummary } from "../types/agent";

const { Paragraph, Text } = Typography;

type OutletContext = {
  agent: AgentDetail;
  reloadAgent: () => void;
};

export default function AgentBenchmarks() {
  const { agent } = useOutletContext<OutletContext>();
  const [benchmarks, setBenchmarks] = useState<VersionBenchmarkSummary[]>([]);
  const [versions, setVersions] = useState<AgentVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [runOpen, setRunOpen] = useState(false);
  const [baselineVersion, setBaselineVersion] = useState("");
  const [candidateVersion, setCandidateVersion] = useState("");
  const [running, setRunning] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [benchmarkData, versionData] = await Promise.all([
        agentsApi.listBenchmarks(agent.id),
        agentsApi.listVersions(agent.id),
      ]);
      setBenchmarks(benchmarkData.benchmarks);
      setVersions(versionData.versions);
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load benchmarks");
    } finally {
      setLoading(false);
    }
  }, [agent.id]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (versions.length >= 2) {
      if (!baselineVersion) setBaselineVersion(versions[0].version);
      if (!candidateVersion) setCandidateVersion(versions[1].version);
    } else if (versions.length === 1) {
      if (!baselineVersion) setBaselineVersion(versions[0].version);
    }
  }, [versions, baselineVersion, candidateVersion]);

  const handleRunBenchmark = async () => {
    const baseline = baselineVersion.trim();
    const candidate = candidateVersion.trim();
    if (!baseline || !candidate) {
      message.warning("Select baseline and candidate versions");
      return;
    }
    if (baseline === candidate) {
      message.warning("Baseline and candidate must differ");
      return;
    }
    setRunning(true);
    try {
      await agentsApi.startBenchmark(agent.id, {
        baseline_version: baseline,
        candidate_version: candidate,
      });
      message.success(`Benchmark completed: ${baseline} → ${candidate}`);
      setRunOpen(false);
      await loadData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Benchmark failed");
    } finally {
      setRunning(false);
    }
  };

  const columns: ColumnsType<VersionBenchmarkSummary> = [
    {
      title: "Version Comparison",
      key: "comparison",
      render: (_, row) => (
        <Space>
          <Text code>{row.baseline_version}</Text>
          <ArrowRightOutlined />
          <Text code>{row.candidate_version}</Text>
        </Space>
      ),
    },
    {
      title: "Score",
      key: "score",
      render: (_, row) => {
        if (row.baseline_score == null || row.candidate_score == null) return "—";
        return (
          <Text>
            {row.baseline_score} → {row.candidate_score}
          </Text>
        );
      },
    },
    {
      title: "Delta",
      dataIndex: "score_delta",
      key: "score_delta",
      render: (value: number | null) =>
        value != null ? (
          <Text type={value >= 0 ? "success" : "danger"}>
            {value >= 0 ? "+" : ""}
            {value}
          </Text>
        ) : (
          "—"
        ),
    },
    {
      title: "Regression",
      dataIndex: "regression_detected",
      key: "regression_detected",
      render: (value: boolean | null) =>
        value == null ? (
          "—"
        ) : value ? (
          <Tag color="error">true</Tag>
        ) : (
          <Tag color="success">false</Tag>
        ),
    },
    {
      title: "Created",
      dataIndex: "started_at",
      key: "started_at",
      render: (value: string) => new Date(value).toLocaleString(),
    },
  ];

  return (
    <Card
      className="ic-panel"
      title={
        <Space>
          <LineChartOutlined />
          Version Benchmarks
        </Space>
      }
      extra={
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => void loadData()} loading={loading}>
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<ExperimentOutlined />}
            onClick={() => setRunOpen(true)}
            disabled={versions.length < 2}
          >
            Run Benchmark
          </Button>
        </Space>
      }
    >
      <Paragraph type="secondary">
        Compare two published versions with the same evaluation suite. Answer whether a new version
        is better than the baseline before deployment.
      </Paragraph>
      {versions.length < 2 ? (
        <Paragraph type="warning">Publish at least two versions to run a benchmark comparison.</Paragraph>
      ) : null}
      <Table
        rowKey="benchmark_id"
        loading={loading}
        columns={columns}
        dataSource={benchmarks}
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: "No benchmarks yet" }}
      />

      <Modal
        title="Run Version Benchmark"
        open={runOpen}
        onCancel={() => setRunOpen(false)}
        onOk={() => void handleRunBenchmark()}
        confirmLoading={running}
        okText="Run"
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text>Baseline version</Text>
            <Select
              style={{ width: "100%", marginTop: 8 }}
              value={baselineVersion || undefined}
              onChange={setBaselineVersion}
              options={versions.map((v) => ({ label: v.version, value: v.version }))}
            />
          </div>
          <div>
            <Text>Candidate version</Text>
            <Select
              style={{ width: "100%", marginTop: 8 }}
              value={candidateVersion || undefined}
              onChange={setCandidateVersion}
              options={versions.map((v) => ({ label: v.version, value: v.version }))}
            />
          </div>
        </Space>
      </Modal>
    </Card>
  );
}

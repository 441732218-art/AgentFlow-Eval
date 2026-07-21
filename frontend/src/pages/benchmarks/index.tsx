/* (c) 2026 AgentFlow-Eval — Benchmark platform */

import React, { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import {
  PlusOutlined,
  PlayCircleOutlined,
  TrophyOutlined,
  ReloadOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/ui/PageHeader";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { benchmarksApi, type Benchmark, type LeaderboardRow } from "@/api";
import { Can } from "@/auth";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

const BENCH_KEY = ["benchmarks"] as const;

const BenchmarksPage: React.FC = () => {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const listQ = useQuery({
    queryKey: BENCH_KEY,
    queryFn: () => benchmarksApi.list(),
  });

  const detailQ = useQuery({
    queryKey: [...BENCH_KEY, selectedId],
    queryFn: () => benchmarksApi.get(selectedId!),
    enabled: !!selectedId,
  });

  const boardQ = useQuery({
    queryKey: [...BENCH_KEY, selectedId, "leaderboard"],
    queryFn: () => benchmarksApi.leaderboard(selectedId!),
    enabled: !!selectedId,
  });

  const createMut = useMutation({
    mutationFn: benchmarksApi.create,
    onSuccess: (bm) => {
      message.success("Benchmark 已创建");
      setCreateOpen(false);
      form.resetFields();
      void qc.invalidateQueries({ queryKey: BENCH_KEY });
      setSelectedId(bm.id);
    },
    onError: (e: Error) => message.error(e.message),
  });

  const runMut = useMutation({
    mutationFn: (vars: { id: string; label: string; model: string }) =>
      benchmarksApi.run(vars.id, {
        label: vars.label,
        agent_config: { model: vars.model, temperature: 0 },
        enqueue: true,
      }),
    onSuccess: (data) => {
      message.success(`Run 已提交 · task=${data.run.task_id || "—"}`);
      void qc.invalidateQueries({ queryKey: [...BENCH_KEY, selectedId] });
      void qc.invalidateQueries({
        queryKey: [...BENCH_KEY, selectedId, "leaderboard"],
      });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const items = listQ.data?.items ?? [];
  const board: LeaderboardRow[] = boardQ.data?.items ?? [];

  const boardCols = useMemo(
    () => [
      { title: "#", dataIndex: "rank", width: 56 },
      { title: "Label", dataIndex: "label" },
      {
        title: "Score",
        dataIndex: "score",
        render: (v: number | null | undefined) =>
          v == null ? "—" : Number(v).toFixed(2),
      },
      {
        title: "Accuracy",
        dataIndex: "accuracy",
        render: (v: number | null | undefined) =>
          v == null ? "—" : Number(v).toFixed(2),
      },
      {
        title: "Quality",
        dataIndex: "quality",
        render: (v: number | null | undefined) =>
          v == null ? "—" : Number(v).toFixed(2),
      },
      {
        title: "Latency ms",
        dataIndex: "latency_ms",
        render: (v: number | null | undefined) =>
          v == null ? "—" : Number(v).toFixed(0),
      },
      {
        title: "Tokens",
        dataIndex: "tokens",
        render: (v: number | null | undefined) => v ?? "—",
      },
      {
        title: "Cost",
        dataIndex: "cost",
        render: (v: number | null | undefined) =>
          v == null ? "—" : `$${Number(v).toFixed(4)}`,
      },
      {
        title: "Status",
        dataIndex: "status",
        render: (s: string) => <Tag>{s}</Tag>,
      },
    ],
    []
  );

  if (listQ.isLoading) return <PageSkeleton variant="cards" />;

  return (
    <div className="ic-page">
      <PageHeader
        title="Benchmark"
        subtitle="行业评测集 · 导入用例 · 调用 Evaluation Engine · 排行榜"
        icon={<ExperimentOutlined />}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => void listQ.refetch()}
            >
              刷新
            </Button>
            <Can perm="benchmark:create">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateOpen(true)}
              >
                新建 Benchmark
              </Button>
            </Can>
          </Space>
        }
      />

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="运行会创建 Task 并走现有评测流水线（不改 Pipeline 内核）"
        description="支持 JSON/CSV 用例；排行榜指标：accuracy / quality / latency / cost / tokens。"
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card title="套件列表" size="small">
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={items}
              onRow={(row: Benchmark) => ({
                onClick: () => setSelectedId(row.id),
                style: {
                  cursor: "pointer",
                  background:
                    row.id === selectedId
                      ? "var(--af-primary-soft, rgba(56,189,248,0.08))"
                      : undefined,
                },
              })}
              columns={[
                { title: "名称", dataIndex: "name" },
                {
                  title: "Cases",
                  dataIndex: "case_count",
                  width: 72,
                  render: (v: number | null | undefined) => v ?? "—",
                },
              ]}
              locale={{ emptyText: "暂无 Benchmark，请先创建" }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={16}>
          {!selectedId ? (
            <Card>
              <Paragraph type="secondary">选择左侧 Benchmark 查看详情与排行榜</Paragraph>
            </Card>
          ) : (
            <Space direction="vertical" size={16} style={{ width: "100%" }}>
              <Card
                title={detailQ.data?.name || selectedId}
                loading={detailQ.isLoading}
                extra={
                  <Can perm="benchmark:create">
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      loading={runMut.isPending}
                      onClick={() => {
                        const label =
                          window.prompt("Run label（排行榜分组）", "baseline") ||
                          "baseline";
                        const model =
                          window.prompt("Agent model", "gpt-4o-mini") ||
                          "gpt-4o-mini";
                        runMut.mutate({ id: selectedId, label, model });
                      }}
                    >
                      运行
                    </Button>
                  </Can>
                }
              >
                <Text type="secondary">{detailQ.data?.description || "—"}</Text>
                <div style={{ marginTop: 12 }}>
                  <Text strong>Cases: </Text>
                  {detailQ.data?.case_count ?? detailQ.data?.cases?.length ?? 0}
                </div>
                {(detailQ.data?.cases?.length ?? 0) > 0 && (
                  <Table
                    style={{ marginTop: 12 }}
                    size="small"
                    rowKey={(r) => r.id || r.user_query}
                    pagination={{ pageSize: 5 }}
                    dataSource={detailQ.data?.cases || []}
                    columns={[
                      { title: "Name", dataIndex: "name", width: 120 },
                      {
                        title: "Query",
                        dataIndex: "user_query",
                        ellipsis: true,
                      },
                      {
                        title: "Expected",
                        dataIndex: "expected_output",
                        ellipsis: true,
                      },
                    ]}
                  />
                )}
              </Card>

              <Card
                title={
                  <Space>
                    <TrophyOutlined /> 排行榜
                  </Space>
                }
                loading={boardQ.isLoading}
                extra={
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => void boardQ.refetch()}
                  >
                    刷新
                  </Button>
                }
              >
                <Table
                  size="small"
                  rowKey="run_id"
                  dataSource={board}
                  columns={boardCols}
                  pagination={false}
                  locale={{ emptyText: "暂无已完成 Run — 运行后 finalize 即可上榜" }}
                />
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      <Modal
        title="新建 Benchmark"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={createMut.isPending}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => {
            let cases: Array<{ user_query: string; expected_output?: string }> =
              [];
            const raw = (values.cases_json || "").trim();
            if (raw) {
              try {
                const parsed = JSON.parse(raw);
                cases = Array.isArray(parsed)
                  ? parsed
                  : parsed.cases || parsed.items || [];
              } catch {
                message.error("Cases JSON 无法解析");
                return;
              }
            }
            createMut.mutate({
              name: values.name,
              description: values.description || "",
              cases,
            });
          }}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: "请输入名称" }]}
          >
            <Input placeholder="e.g. Tool-Use Bench v1" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="cases_json"
            label="Cases (JSON 数组，可选)"
            extra='示例: [{"user_query":"hi","expected_output":"hello"}]'
          >
            <TextArea rows={6} placeholder="[]" />
          </Form.Item>
          <Form.Item name="format_hint" label="后续导入">
            <Select
              disabled
              defaultValue="json"
              options={[
                { value: "json", label: "POST /benchmarks/{id}/import format=json" },
                { value: "csv", label: "CSV: name,user_query,expected_output" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BenchmarksPage;

import { useCallback, useEffect, useState } from "react";
import {
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Select,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { PageShell } from "@/components/common/PageShell";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { salesDemoApi } from "../api/salesDemo";
import type { SalesDemoCase, SalesDemoResult, SalesToolCall } from "../types/salesDemo";

const { Paragraph, Text } = Typography;

export default function SalesDemoPage() {
  const [cases, setCases] = useState<SalesDemoCase[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | undefined>();
  const [result, setResult] = useState<SalesDemoResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  const loadCases = useCallback(async () => {
    setLoading(true);
    try {
      const data = await salesDemoApi.listCases();
      setCases(data.cases);
      if (data.cases.length > 0) {
        setSelectedCaseId(data.cases[0].case_id);
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to load sales cases");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCases();
  }, [loadCases]);

  const runDemo = async () => {
    setRunning(true);
    try {
      const response = await salesDemoApi.runDemo({ case_id: selectedCaseId });
      setResult(response.demo);
      message.success("Sales demo completed");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "Failed to run sales demo");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return <PageSkeleton variant="dashboard" />;
  }

  const toolColumns: ColumnsType<SalesToolCall> = [
    { title: "Tool", dataIndex: "tool_name", key: "tool_name", render: (v) => <Text code>{v}</Text> },
    {
      title: "Arguments",
      dataIndex: "arguments",
      key: "arguments",
      render: (v: Record<string, unknown>) => (
        <Text type="secondary">{JSON.stringify(v)}</Text>
      ),
    },
  ];

  return (
    <PageShell
      title="Sales Demo"
      subtitle="AI Foreign Trade Sales Agent — real business pilot scenario"
    >
      <Card className="ic-panel" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Select
              style={{ width: "100%", maxWidth: 520 }}
              value={selectedCaseId}
              onChange={setSelectedCaseId}
              options={cases.map((item) => ({
                value: item.case_id,
                label: `${item.customer_id} — ${item.customer_inquiry.slice(0, 60)}...`,
              }))}
            />
          </Col>
          <Col>
            <Button type="primary" loading={running} onClick={() => void runDemo()}>
              Run Sales Demo
            </Button>
          </Col>
        </Row>
      </Card>

      {result ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="Customer & Inquiry">
              <Descriptions bordered size="small" column={1}>
                <Descriptions.Item label="Customer">
                  {(result.customer?.company as string) ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Customer ID">
                  {(result.customer?.customer_id as string) ?? "—"}
                </Descriptions.Item>
                <Descriptions.Item label="Inquiry">{result.inquiry}</Descriptions.Item>
                <Descriptions.Item label="Status">
                  <Tag color={result.status === "SUCCESS" ? "success" : "error"}>{result.status}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="Tool Calls" style={{ marginTop: 16 }}>
              <Table
                size="small"
                rowKey={(row, index) => `${row.tool_name}-${index}`}
                columns={toolColumns}
                dataSource={result.tool_calls}
                pagination={false}
              />
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="Generated Reply">
              {result.email_draft ? (
                <>
                  <Paragraph><Text strong>Subject:</Text> {result.email_draft.subject}</Paragraph>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{result.email_draft.body}</pre>
                </>
              ) : (
                "—"
              )}
            </Card>

            <Card title="Evaluation Score" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={12}>
                  <Statistic title="Total" value={result.evaluation_score.total} suffix="/ 100" />
                </Col>
                <Col span={12}>
                  <Statistic title="Product Accuracy" value={result.evaluation_score.product_accuracy} />
                </Col>
                <Col span={12}>
                  <Statistic title="Response Quality" value={result.evaluation_score.response_quality} />
                </Col>
                <Col span={12}>
                  <Statistic title="Customer Match" value={result.evaluation_score.customer_match} />
                </Col>
                <Col span={12}>
                  <Statistic title="Business Compliance" value={result.evaluation_score.business_compliance} />
                </Col>
              </Row>
            </Card>
          </Col>
        </Row>
      ) : null}
    </PageShell>
  );
}

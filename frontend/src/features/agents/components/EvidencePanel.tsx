import { Card, Descriptions, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { ExecutionEvidence, ToolHistoryItem } from "../types/agent";

const { Text } = Typography;

interface EvidencePanelProps {
  evidence: ExecutionEvidence | null;
  loading?: boolean;
}

export function EvidencePanel({ evidence, loading }: EvidencePanelProps) {
  if (!evidence && !loading) {
    return null;
  }

  const toolColumns: ColumnsType<ToolHistoryItem> = [
    { title: "Tool", dataIndex: "tool_name", key: "tool_name", render: (v) => v ?? "—" },
    { title: "Event", dataIndex: "event_type", key: "event_type" },
    { title: "Status", dataIndex: "status", key: "status", render: (v) => v ?? "—" },
    {
      title: "Duration (ms)",
      dataIndex: "duration_ms",
      key: "duration_ms",
      render: (v) => (v != null ? v : "—"),
    },
  ];

  return (
    <Card className="ic-panel" title="Evidence Panel" loading={loading} style={{ marginBottom: 24 }}>
      <Descriptions bordered size="small" column={1}>
        <Descriptions.Item label="Agent Version">
          {evidence?.agent_version ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Deployment">
          {evidence?.deployment_environment ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Tenant">
          {evidence?.tenant_id ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Actor">
          {evidence?.actor_id ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Release Decision">
          {evidence?.release_decision ? (
            <Tag color={evidence.release_decision === "REJECT" ? "error" : "success"}>
              {evidence.release_decision}
            </Tag>
          ) : (
            "—"
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Evaluation Score">
          {evidence?.evaluation_score != null ? evidence.evaluation_score : "—"}
        </Descriptions.Item>
      </Descriptions>

      {evidence?.tool_history?.length ? (
        <div style={{ marginTop: 16 }}>
          <Text strong>Tool History</Text>
          <Table
            size="small"
            rowKey={(row, index) => `${row.tool_name}-${index}`}
            columns={toolColumns}
            dataSource={evidence.tool_history}
            pagination={false}
            style={{ marginTop: 8 }}
          />
        </div>
      ) : null}
    </Card>
  );
}

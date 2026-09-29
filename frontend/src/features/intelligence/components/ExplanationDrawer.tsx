import { Descriptions, Drawer, Empty, Spin, Tag, Typography } from "antd";

const { Paragraph, Text } = Typography;

export type ExplanationDrawerPayload = {
  title: string;
  summary?: string | null;
  reason?: string | null;
  posture?: string | null;
  evidenceRefs?: Array<{ type: string; id: string }>;
  snapshotRefs?: Array<{ snapshot_id: string; snapshot_type: string }>;
  relatedIds?: string[];
};

type Props = {
  open: boolean;
  loading?: boolean;
  error?: string | null;
  payload: ExplanationDrawerPayload | null;
  onClose: () => void;
};

export function ExplanationDrawer({ open, loading, error, payload, onClose }: Props) {
  return (
    <Drawer
      title={payload?.title || "Explanation"}
      open={open}
      onClose={onClose}
      width={480}
      destroyOnClose
    >
      {loading ? <Spin /> : null}
      {!loading && error ? (
        <Empty description={error} />
      ) : null}
      {!loading && !error && payload ? (
        <Descriptions column={1} size="small" bordered>
          {payload.posture ? (
            <Descriptions.Item label="Posture">
              <Tag>{payload.posture}</Tag>
            </Descriptions.Item>
          ) : null}
          {payload.summary ? (
            <Descriptions.Item label="Summary">
              <Paragraph style={{ marginBottom: 0 }}>{payload.summary}</Paragraph>
            </Descriptions.Item>
          ) : null}
          {payload.reason ? (
            <Descriptions.Item label="Reason">
              <Paragraph style={{ marginBottom: 0 }}>{payload.reason}</Paragraph>
            </Descriptions.Item>
          ) : null}
          {payload.evidenceRefs?.length ? (
            <Descriptions.Item label="Evidence">
              {payload.evidenceRefs.map((ref) => (
                <div key={`${ref.type}:${ref.id}`}>
                  <Text code>
                    {ref.type}:{ref.id}
                  </Text>
                </div>
              ))}
            </Descriptions.Item>
          ) : null}
          {payload.snapshotRefs?.length ? (
            <Descriptions.Item label="Snapshots">
              {payload.snapshotRefs.map((ref) => (
                <div key={`${ref.snapshot_type}:${ref.snapshot_id}`}>
                  <Text code>
                    {ref.snapshot_type}:{ref.snapshot_id}
                  </Text>
                </div>
              ))}
            </Descriptions.Item>
          ) : null}
          {payload.relatedIds?.length ? (
            <Descriptions.Item label="Related">
              {payload.relatedIds.map((id) => (
                <Tag key={id}>{id}</Tag>
              ))}
            </Descriptions.Item>
          ) : null}
        </Descriptions>
      ) : null}
      {!loading && !error && !payload ? <Empty description="No explanation" /> : null}
    </Drawer>
  );
}

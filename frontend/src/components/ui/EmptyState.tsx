import type { ReactNode } from "react";
import { Button, Empty, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";

const { Text } = Typography;

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Custom action node; takes precedence over actionLabel/onAction */
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({
  title = "暂无数据",
  description = "开始创建你的第一个评测任务吧",
  actionLabel = "创建任务",
  onAction,
  action,
  icon,
}: EmptyStateProps) {
  return (
    <div
      className="af-glass"
      style={{
        padding: "56px 24px",
        textAlign: "center",
        borderStyle: "dashed",
      }}
    >
      <Empty
        image={icon || Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            <Text strong style={{ fontSize: 16, display: "block", marginBottom: 4 }}>
              {title}
            </Text>
            <Text type="secondary">{description}</Text>
          </div>
        }
      >
        {action ? (
          <div style={{ marginTop: 8 }}>{action}</div>
        ) : (
          onAction && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={onAction}
              style={{ background: "var(--af-gradient)", border: "none", marginTop: 8 }}
            >
              {actionLabel}
            </Button>
          )
        )}
      </Empty>
    </div>
  );
}

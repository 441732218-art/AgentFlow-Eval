import type { ReactNode } from "react";
import { Button, Empty, Typography } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import clsx from "clsx";

const { Text } = Typography;

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  /** Custom action node; takes precedence over actionLabel/onAction */
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}

export function EmptyState({
  title = "暂无数据",
  description = "开始创建你的第一个评测任务吧",
  actionLabel = "创建任务",
  onAction,
  action,
  icon,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx("ic-empty", "ic-panel", className)}>
      <Empty
        image={icon || Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            <Text strong className="ic-empty__title">
              {title}
            </Text>
            <Text type="secondary" className="ic-empty__desc">
              {description}
            </Text>
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
              className="ic-btn-gradient"
              style={{ marginTop: 8 }}
            >
              {actionLabel}
            </Button>
          )
        )}
      </Empty>
    </div>
  );
}

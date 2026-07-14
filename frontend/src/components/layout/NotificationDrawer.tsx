/* Activity notifications — change events + live tasks snapshot */

import { useMemo } from "react";
import { Drawer, List, Typography, Space, Button, Empty, Tag, Badge, Divider } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  CheckOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { formatDateTime } from "@/utils/format";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  useNotificationStore,
  type ActivityEvent,
} from "@/stores/useNotificationStore";
import { useI18nStore } from "@/i18n";
import { useTasks } from "@/hooks";
import type { Task } from "@/types";

const { Text, Paragraph } = Typography;

interface NotificationDrawerProps {
  open: boolean;
  onClose: () => void;
}

function iconFor(status: string) {
  if (status === "completed") return <CheckCircleOutlined style={{ color: "var(--af-success)" }} />;
  if (status === "failed" || status === "timeout")
    return <CloseCircleOutlined style={{ color: "var(--af-danger)" }} />;
  if (["running", "queued", "judging", "waiting_tool"].includes(status))
    return <ClockCircleOutlined style={{ color: "var(--af-primary)" }} />;
  return <ExperimentOutlined style={{ color: "var(--af-accent)" }} />;
}

export function NotificationDrawer({ open, onClose }: NotificationDrawerProps) {
  const navigate = useNavigate();
  const t = useI18nStore((s) => s.t);
  const events = useNotificationStore((s) => s.events);
  const markRead = useNotificationStore((s) => s.markRead);
  const markAllRead = useNotificationStore((s) => s.markAllRead);
  const clear = useNotificationStore((s) => s.clear);
  const lastPolledAt = useNotificationStore((s) => s.lastPolledAt);
  const transport = useNotificationStore((s) => s.transport);
  const { data: taskData } = useTasks({ page: 1, page_size: 20 });

  const items = useMemo(() => {
    const list = [...events];
    const weight = (s: string) => {
      if (["running", "queued", "judging", "waiting_tool"].includes(s)) return 0;
      if (s === "failed" || s === "timeout") return 1;
      if (s === "completed") return 2;
      return 3;
    };
    list.sort((a, b) => {
      if (a.read !== b.read) return a.read ? 1 : -1;
      const w = weight(a.status) - weight(b.status);
      if (w !== 0) return w;
      return (b.at || "").localeCompare(a.at || "");
    });
    return list.slice(0, 30);
  }, [events]);

  const liveTasks = useMemo(() => {
    return (taskData?.items || [])
      .filter((t: Task) =>
        ["running", "queued", "judging", "waiting_tool"].includes(t.status)
      )
      .slice(0, 8);
  }, [taskData?.items]);

  const unread = items.filter((e) => !e.read).length;
  const activeCount = liveTasks.length || items.filter((e) =>
    ["running", "queued", "judging", "waiting_tool"].includes(e.status)
  ).length;

  const openItem = (ev: ActivityEvent) => {
    markRead(ev.id);
    onClose();
    navigate(`/tasks/${ev.taskId}`);
  };

  return (
    <Drawer
      title={
        <Space>
          <span>{t("notify.title")}</span>
          {activeCount > 0 && (
            <Tag color="processing" icon={<ThunderboltOutlined />}>
              {activeCount} {t("notify.active")}
            </Tag>
          )}
          {unread > 0 && <Badge count={unread} size="small" />}
        </Space>
      }
      placement="right"
      width={400}
      open={open}
      onClose={onClose}
      extra={
        <Space size={4}>
          <Button type="text" size="small" icon={<CheckOutlined />} onClick={() => markAllRead()}>
            {t("notify.markAll")}
          </Button>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={() => clear()}>
            {t("notify.clear")}
          </Button>
        </Space>
      }
      styles={{
        body: { paddingTop: 8 },
        header: { borderBottom: "1px solid var(--af-border)" },
      }}
    >
      <div style={{ marginBottom: 10 }}>
        <Space size={6} wrap>
          <Tag color={transport === "ws" ? "success" : "cyan"} style={{ borderRadius: 999 }}>
            {transport === "ws" ? t("notify.ws") : t("notify.live")}
            {lastPolledAt ? ` · ${formatDateTime(lastPolledAt)}` : ""}
          </Tag>
        </Space>
      </div>

      {liveTasks.length > 0 && (
        <>
          <Text type="secondary" style={{ fontSize: 11, letterSpacing: "0.04em" }}>
            LIVE
          </Text>
          <List
            size="small"
            dataSource={liveTasks}
            style={{ marginBottom: 8 }}
            renderItem={(task) => (
              <List.Item
                className="af-card-hover"
                style={{ cursor: "pointer", borderRadius: 10, padding: "8px 6px" }}
                onClick={() => {
                  onClose();
                  navigate(`/tasks/${task.id}`);
                }}
              >
                <List.Item.Meta
                  avatar={iconFor(task.status)}
                  title={<Text style={{ fontSize: 13 }}>{task.name}</Text>}
                  description={<StatusBadge status={task.status} />}
                />
              </List.Item>
            )}
          />
          <Divider style={{ margin: "8px 0 12px" }} />
        </>
      )}

      {items.length === 0 ? (
        <Empty description={t("notify.empty")} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <List
          itemLayout="horizontal"
          dataSource={items}
          renderItem={(ev) => (
            <List.Item
              className="af-card-hover"
              style={{
                cursor: "pointer",
                borderRadius: 12,
                padding: "12px 10px",
                border: ev.read
                  ? "1px solid transparent"
                  : "1px solid var(--af-border-strong)",
                background: ev.read ? "transparent" : "var(--af-primary-soft)",
                marginBottom: 6,
              }}
              onClick={() => openItem(ev)}
            >
              <List.Item.Meta
                avatar={
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: 10,
                      background: "var(--af-bg-muted)",
                      display: "grid",
                      placeItems: "center",
                      fontSize: 16,
                    }}
                  >
                    {iconFor(ev.status)}
                  </div>
                }
                title={
                  <Space size={6}>
                    {!ev.read && (
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: "50%",
                          background: "var(--af-primary)",
                          display: "inline-block",
                        }}
                      />
                    )}
                    <Text style={{ fontSize: 13, fontWeight: 600 }}>{ev.message}</Text>
                  </Space>
                }
                description={
                  <Space direction="vertical" size={4} style={{ width: "100%" }}>
                    <Space size={6} wrap>
                      <StatusBadge status={ev.status} />
                      {ev.prevStatus && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {ev.prevStatus} → {ev.status}
                        </Text>
                      )}
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {formatDateTime(ev.at)}
                      </Text>
                    </Space>
                    <Paragraph type="secondary" ellipsis style={{ margin: 0, fontSize: 12 }}>
                      {ev.taskName}
                    </Paragraph>
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      )}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        <Button
          type="link"
          onClick={() => {
            onClose();
            navigate("/tasks");
          }}
        >
          {t("notify.allTasks")}
        </Button>
      </div>
    </Drawer>
  );
}

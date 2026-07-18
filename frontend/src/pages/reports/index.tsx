/* (c) 2026 AgentFlow-Eval */
/* Reports list — card style */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Tag,
  Button,
  Space,
  Select,
  Alert,
  Typography,
  Row,
  Col,
  Pagination,
} from "antd";
import {
  EyeOutlined,
  ReloadOutlined,
  FileTextOutlined,
  BarChartOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import { useTasks } from "@/hooks";
import { formatDateTime } from "@/utils/format";
import type { Task } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge, OwnerBadge } from "@/components/ui/StatusBadge";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { useI18nStore } from "@/i18n";

const { Text, Paragraph } = Typography;

const STATUS_OPTIONS = [
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "cancelled", label: "已取消" },
  { value: "timeout", label: "超时" },
  { value: "", label: "全部终态" },
];

export default function ReportsPage() {
  const navigate = useNavigate();
  const t = useI18nStore((s) => s.t);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("completed");

  const { data, isLoading, error, refetch } = useTasks({
    page,
    page_size: 12,
    status: status || undefined,
  });

  const terminal = new Set(["completed", "failed", "cancelled", "timeout"]);
  const items = (data?.items ?? []).filter((t) => (status ? true : terminal.has(t.status)));

  if (error) {
    return (
      <Alert
        type="error"
        message="加载报告列表失败"
        description={(error as Error).message}
        showIcon
        action={
          <Button size="small" onClick={() => refetch()}>
            重试
          </Button>
        }
      />
    );
  }

  return (
    <div className="ic-page af-page">
      <PageHeader
        title={t("reports.title")}
        subtitle={t("reports.subtitle")}
        icon={<BarChartOutlined />}
        extra={
          <Space>
            <Select
              style={{ width: 140 }}
              value={status}
              options={STATUS_OPTIONS}
              onChange={(v) => {
                setStatus(v);
                setPage(1);
              }}
            />
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t("common.refresh")}
            </Button>
          </Space>
        }
      />

      {isLoading ? (
        <PageSkeleton variant="cards" rows={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t("reports.empty")}
          description={t("reports.emptyDesc")}
          action={
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tasks/create")}>
                {t("tasks.create")}
              </Button>
              <Button onClick={() => navigate("/tasks")}>{t("dashboard.allTasks")}</Button>
            </Space>
          }
        />
      ) : (
        <>
          <Row gutter={[16, 16]}>
            {items.map((record: Task) => (
              <Col xs={24} sm={12} xl={8} key={record.id}>
                <Card
                  className="af-glass af-card-hover"
                  styles={{ body: { padding: 18 } }}
                  onClick={() => navigate(`/reports/${record.id}`)}
                  style={{ cursor: "pointer", height: "100%" }}
                >
                  <Space style={{ marginBottom: 12 }} wrap>
                    <FileTextOutlined style={{ color: "var(--af-primary)" }} />
                    <StatusBadge status={record.status} />
                    <OwnerBadge owner={record.created_by} />
                    {record.is_archived && <Tag>已归档</Tag>}
                  </Space>
                  <Text strong style={{ fontSize: 16, display: "block", marginBottom: 8 }}>
                    {record.name}
                  </Text>
                  <Paragraph type="secondary" ellipsis={{ rows: 2 }} style={{ minHeight: 40 }}>
                    {record.description || "无描述"}
                  </Paragraph>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginTop: 12,
                      paddingTop: 12,
                      borderTop: "1px solid var(--af-border)",
                    }}
                  >
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {record.test_suite_count} 用例 · {formatDateTime(record.created_at)}
                    </Text>
                    <Button
                      type="link"
                      size="small"
                      icon={<EyeOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/reports/${record.id}`);
                      }}
                    >
                      {t("reports.view")}
                    </Button>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
            <Pagination
              current={page}
              pageSize={12}
              total={data?.total ?? 0}
              onChange={setPage}
              showSizeChanger={false}
            />
          </div>
        </>
      )}
    </div>
  );
}

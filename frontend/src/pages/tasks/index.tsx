import { useState, useEffect, useRef, useMemo, memo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Button,
  Select,
  Input,
  Space,
  Card,
  Alert,
  Modal,
  message,
  Typography,
  Row,
  Col,
  Segmented,
  Pagination,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  EyeOutlined,
  BarChartOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  SearchOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useTasks, useExecuteTask, useDeleteTask } from "@/hooks";
import type { Task } from "@/types";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge, OwnerBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { QuotaStrip } from "@/components/billing/QuotaStrip";
import { formatDateTime } from "@/utils/format";
import { useI18nStore } from "@/i18n";

const { Text, Paragraph } = Typography;

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "created", label: "Created" },
  { value: "queued", label: "Queued" },
  { value: "running", label: "Running" },
  { value: "judging", label: "Judging" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
  { value: "timeout", label: "Timeout" },
];

const QUICK_FILTERS = [
  { value: "", label: "全部" },
  { value: "running", label: "运行中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "created", label: "待执行" },
];

const TaskCard = memo(function TaskCard({
  task,
  onView,
  onReport,
  onExecute,
  onDelete,
  executing,
  deleting,
}: {
  task: Task;
  onView: () => void;
  onReport: () => void;
  onExecute: () => void;
  onDelete: () => void;
  executing?: boolean;
  deleting?: boolean;
}) {
  const isLive = ["running", "queued", "judging"].includes(task.status);
  return (
    <Card
      className="af-card-hover af-glass"
      styles={{ body: { padding: 18 } }}
      style={{ height: "100%", cursor: "pointer" }}
      onClick={onView}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 12 }}>
        <Space size={6} wrap>
          <StatusBadge status={task.status} />
          {isLive && <span className="af-live-dot" title="进行中" />}
        </Space>
        <OwnerBadge owner={task.created_by} />
      </div>

      <Text strong style={{ fontSize: 16, display: "block", marginBottom: 6, lineHeight: 1.35 }}>
        {task.name}
      </Text>
      <Paragraph
        type="secondary"
        ellipsis={{ rows: 2 }}
        style={{ minHeight: 44, marginBottom: 14, fontSize: 13 }}
      >
        {task.description || "暂无描述"}
      </Paragraph>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "10px 12px",
          borderRadius: 10,
          background: "var(--af-bg-muted)",
          marginBottom: 14,
        }}
      >
        <div>
          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
            用例数
          </Text>
          <Text strong>{task.test_suite_count ?? 0}</Text>
        </div>
        <div style={{ textAlign: "right" }}>
          <Text type="secondary" style={{ fontSize: 11, display: "block" }}>
            创建时间
          </Text>
          <Text style={{ fontSize: 12 }}>{formatDateTime(task.created_at)}</Text>
        </div>
      </div>

      <Space size={6} wrap onClick={(e) => e.stopPropagation()}>
        <Button size="small" icon={<EyeOutlined />} onClick={onView}>
          详情
        </Button>
        {["completed", "partial", "failed"].includes(task.status) && (
          <Button size="small" icon={<BarChartOutlined />} onClick={onReport}>
            报告
          </Button>
        )}
        {task.status === "created" && (
          <Button
            size="small"
            type="primary"
            ghost
            icon={<PlayCircleOutlined />}
            loading={executing}
            onClick={onExecute}
          >
            执行
          </Button>
        )}
        <Tooltip title="删除">
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={deleting}
            onClick={onDelete}
          />
        </Tooltip>
      </Space>
    </Card>
  );
});

const TASK_FILTER_KEY = "agentflow_task_filters";

function loadPersistedFilters(): { status?: string; view?: "card" | "table" } {
  try {
    const raw = localStorage.getItem(TASK_FILTER_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as { status?: string; view?: "card" | "table" };
  } catch {
    return {};
  }
}

function writeFiltersToUrl(
  setSearchParams: ReturnType<typeof useSearchParams>[1],
  searchParams: URLSearchParams,
  patch: { status?: string; view?: "card" | "table"; q?: string }
) {
  const next = new URLSearchParams(searchParams);
  if (patch.status !== undefined) {
    if (patch.status) next.set("status", patch.status);
    else next.delete("status");
  }
  if (patch.view !== undefined) {
    if (patch.view && patch.view !== "card") next.set("view", patch.view);
    else next.delete("view");
  }
  if (patch.q !== undefined) {
    if (patch.q) next.set("q", patch.q);
    else next.delete("q");
  }
  if (next.toString() !== searchParams.toString()) {
    setSearchParams(next, { replace: true });
  }
  try {
    localStorage.setItem(
      TASK_FILTER_KEY,
      JSON.stringify({
        status: next.get("status") || "",
        view: (next.get("view") as "card" | "table") || "card",
      })
    );
  } catch {
    /* ignore */
  }
}

export default function TaskListPage() {
  const navigate = useNavigate();
  const t = useI18nStore((s) => s.t);
  const [searchParams, setSearchParams] = useSearchParams();
  const persisted = useMemo(() => loadPersistedFilters(), []);

  // URL is source of truth; hydrate once from localStorage if URL empty
  useEffect(() => {
    if (!searchParams.get("status") && !searchParams.get("view") && (persisted.status || persisted.view)) {
      writeFiltersToUrl(setSearchParams, searchParams, {
        status: persisted.status || "",
        view: persisted.view || "card",
      });
    }
    // only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const status = searchParams.get("status") || "";
  const view = (searchParams.get("view") as "card" | "table") || "card";
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState(() => searchParams.get("q") || "");
  const [debouncedSearch, setDebouncedSearch] = useState(() => searchParams.get("q") || "");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync search box from URL (?q=)
  useEffect(() => {
    const q = searchParams.get("q") || "";
    setSearch(q);
    setDebouncedSearch(q);
    setPage(1);
  }, [searchParams]);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 400);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [search]);

  const setStatus = (s: string) => {
    setPage(1);
    writeFiltersToUrl(setSearchParams, searchParams, { status: s, view });
  };

  const setView = (v: "card" | "table") => {
    writeFiltersToUrl(setSearchParams, searchParams, { status, view: v });
  };

  const { data, isLoading, error, refetch } = useTasks({
    page,
    page_size: 12,
    status: status || undefined,
  });

  const executeMutation = useExecuteTask();
  const deleteMutation = useDeleteTask();

  const items = useMemo(() => {
    const list = data?.items || [];
    if (!debouncedSearch.trim()) return list;
    const q = debouncedSearch.toLowerCase();
    return list.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        (t.description || "").toLowerCase().includes(q) ||
        (t.created_by || "").toLowerCase().includes(q)
    );
  }, [data?.items, debouncedSearch]);

  const handleExecute = (taskId: string) => {
    executeMutation.mutate(taskId, {
      onSuccess: () => {
        message.success("任务已提交执行");
        refetch();
      },
      onError: (err: Error & { status?: number }) => {
        const msg = err?.message || "执行失败";
        if (err?.status === 402) {
          message.error({ content: msg, duration: 5 });
        } else {
          message.error(msg);
        }
      },
    });
  };

  const handleDelete = (taskId: string) => {
    Modal.confirm({
      title: "删除任务",
      content: "此操作不可撤销，关联用例与轨迹将一并删除。",
      okText: "删除",
      okType: "danger",
      cancelText: "取消",
      onOk: () =>
        deleteMutation.mutateAsync(taskId).then(() => {
          message.success("已删除");
          refetch();
        }),
    });
  };

  if (error) {
    return (
      <div className="ic-page af-page">
        <Alert
          type="error"
          showIcon
          message="加载任务失败"
          description={(error as Error)?.message}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>
              重试
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="ic-page af-page">
      <PageHeader
        title={t("tasks.title")}
        subtitle={t("tasks.subtitle")}
        icon={<ExperimentOutlined />}
        extra={
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              {t("common.refresh")}
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate("/tasks/create")}
              style={{ background: "var(--af-gradient)", border: "none" }}
            >
              {t("tasks.create")}
            </Button>
          </Space>
        }
      />

      <QuotaStrip compact />

      {/* Filters bar */}
      <Card
        className="af-glass"
        styles={{ body: { padding: "14px 16px" } }}
        style={{ marginBottom: 20 }}
      >
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} md={8}>
            <Input
              allowClear
              prefix={<SearchOutlined style={{ color: "var(--af-text-muted)" }} />}
              placeholder={t("tasks.search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              size="large"
            />
          </Col>
          <Col xs={24} md={10}>
            <Segmented
              block
              value={status || ""}
              onChange={(v) => {
                setStatus(String(v));
                setPage(1);
              }}
              options={QUICK_FILTERS}
            />
          </Col>
          <Col xs={24} md={6} style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Select
              value={status}
              onChange={(v) => {
                setStatus(v);
                setPage(1);
              }}
              options={STATUS_OPTIONS}
              style={{ minWidth: 120, flex: 1 }}
            />
            <Segmented
              value={view}
              onChange={(v) => setView(v as "card" | "table")}
              options={[
                { value: "card", icon: <AppstoreOutlined /> },
                { value: "table", icon: <UnorderedListOutlined /> },
              ]}
            />
          </Col>
        </Row>
      </Card>

      {isLoading ? (
        <PageSkeleton variant="cards" rows={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title={t("tasks.empty")}
          description={status || debouncedSearch ? "试试调整筛选条件" : "创建第一个评测任务开始吧"}
          actionLabel={t("tasks.create")}
          onAction={() => navigate("/tasks/create")}
        />
      ) : view === "card" ? (
        <>
          <Row gutter={[16, 16]}>
            {items.map((task) => (
              <Col xs={24} sm={12} xl={8} key={task.id}>
                <TaskCard
                  task={task}
                  onView={() => navigate(`/tasks/${task.id}`)}
                  onReport={() => navigate(`/reports/${task.id}`)}
                  onExecute={() => handleExecute(task.id)}
                  onDelete={() => handleDelete(task.id)}
                  executing={executeMutation.isPending}
                  deleting={deleteMutation.isPending}
                />
              </Col>
            ))}
          </Row>
          <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
            <Pagination
              current={page}
              pageSize={12}
              total={data?.total || 0}
              onChange={setPage}
              showSizeChanger={false}
              showTotal={(t) => `共 ${t} 个任务`}
            />
          </div>
        </>
      ) : (
        <Card className="af-glass" styles={{ body: { padding: 0 } }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid var(--af-border)", textAlign: "left" }}>
                  {["名称", "状态", "Owner", "用例", "创建", "操作"].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: "12px 16px",
                        color: "var(--af-text-secondary)",
                        fontWeight: 600,
                        fontSize: 12,
                        textTransform: "uppercase",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((task) => (
                  <tr
                    key={task.id}
                    style={{ borderBottom: "1px solid var(--af-border)", cursor: "pointer" }}
                    onClick={() => navigate(`/tasks/${task.id}`)}
                  >
                    <td style={{ padding: "14px 16px" }}>
                      <Text strong>{task.name}</Text>
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <StatusBadge status={task.status} />
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      <OwnerBadge owner={task.created_by} />
                    </td>
                    <td style={{ padding: "14px 16px" }}>{task.test_suite_count}</td>
                    <td style={{ padding: "14px 16px", whiteSpace: "nowrap" }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {formatDateTime(task.created_at)}
                      </Text>
                    </td>
                    <td style={{ padding: "14px 16px" }} onClick={(e) => e.stopPropagation()}>
                      <Space size={4}>
                        <Button size="small" type="link" onClick={() => navigate(`/tasks/${task.id}`)}>
                          详情
                        </Button>
                        {task.status === "created" && (
                          <Button size="small" type="link" onClick={() => handleExecute(task.id)}>
                            执行
                          </Button>
                        )}
                      </Space>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="af-table-footer">
            <Pagination
              current={page}
              pageSize={12}
              total={data?.total || 0}
              onChange={setPage}
              showSizeChanger={false}
            />
          </div>
        </Card>
      )}
    </div>
  );
}

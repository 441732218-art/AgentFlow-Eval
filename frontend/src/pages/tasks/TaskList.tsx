import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom";
import {
  Table,
  Tag,
  Button,
  Select,
  Input,
  Space,
  Card,
  Empty,
  Alert,
  Spin,
  Modal,
  message,
  Typography,
} from "antd";
import {
  PlusOutlined,
  EyeOutlined,
  BarChartOutlined,
  PlayCircleOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { useTasks, useExecuteTask, useDeleteTask } from "@/hooks";
import type { Task } from "@/types";

const { Text } = Typography;

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

const STATUS_COLORS: Record<string, string> = {
  pending: "default",
  running: "processing",
  completed: "success",
  failed: "error",
};

function formatDate(date: string | null): string {
  if (!date) return "-";
  const d = new Date(date);
  return d.toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function TaskListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search input (500ms)
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 500);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [search]);

  // Fetch tasks
  const params: Record<string, unknown> = { page, page_size: 20 };
  if (status) params.status = status;
  if (debouncedSearch) params.search = debouncedSearch;

  const { data, isLoading, error, refetch } = useTasks(
    params as { page?: number; page_size?: number; status?: string }
  );

  // Mutations
  const executeMutation = useExecuteTask();
  const deleteMutation = useDeleteTask();

  const handleExecute = (taskId: string) => {
    executeMutation.mutate(taskId, {
      onSuccess: () => {
        message.success("Task submitted for execution.");
        refetch();
      },
      onError: () => message.error("Failed to execute task."),
    });
  };

  const handleDelete = (taskId: string) => {
    Modal.confirm({
      title: "Delete Task",
      content: "Are you sure you want to delete this task? This action cannot be undone.",
      okText: "Delete",
      okType: "danger",
      cancelText: "Cancel",
      onOk: () => {
        deleteMutation.mutate(taskId, {
          onSuccess: () => {
            message.success("Task deleted.");
            refetch();
          },
          onError: () => message.error("Failed to delete task."),
        });
      },
    });
  };

  // Columns
  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: Task) => (
        <Button type="link" onClick={() => navigate(`/tasks/${record.id}`)} style={{ padding: 0 }}>
          {name}
        </Button>
      ),
    },
    {
      title: "Description",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      width: 250,
      render: (desc: string) => desc || <Text type="secondary">-</Text>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (s: string) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Suites",
      dataIndex: "test_suite_count",
      key: "test_suite_count",
      width: 80,
      align: "center" as const,
    },
    {
      title: "Created",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (d: string | null) => formatDate(d),
    },
    {
      title: "Actions",
      key: "actions",
      width: 280,
      render: (_: unknown, record: Task) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/tasks/${record.id}`)}>
            View
          </Button>
          {record.status === "completed" && (
            <Button
              size="small"
              icon={<BarChartOutlined />}
              onClick={() => navigate(`/reports/${record.id}`)}
            >
              Report
            </Button>
          )}
          {record.status === "pending" && (
            <Button
              size="small"
              icon={<PlayCircleOutlined />}
              loading={executeMutation.isPending}
              onClick={() => handleExecute(record.id)}
            >
              Execute
            </Button>
          )}
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            loading={deleteMutation.isPending}
            onClick={() => handleDelete(record.id)}
          >
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  // Error state
  if (error) {
    return (
      <Card>
        <Alert
          message="Failed to load tasks"
          description={(error as Error)?.message || "An unexpected error occurred."}
          type="error"
          showIcon
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>
              Retry
            </Button>
          }
        />
      </Card>
    );
  }

  // Empty state
  if (!isLoading && data && data.items.length === 0) {
    return (
      <Card>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="No tasks found. Create your first evaluation task!"
        >
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/tasks/create")}
          >
            Create Task
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <Card
      title="Evaluation Tasks"
      extra={
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/tasks/create")}
          >
            Create Task
          </Button>
        </Space>
      }
    >
      {/* Filters */}
      <Space style={{ marginBottom: 16, width: "100%" }} size="middle">
        <Input
          placeholder="Search tasks..."
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 280 }}
        />
        <Select
          value={status}
          onChange={(val) => {
            setStatus(val);
            setPage(1);
          }}
          options={STATUS_OPTIONS}
          style={{ width: 160 }}
        />
        {isLoading && <Spin size="small" />}
      </Space>

      {/* Table */}
      <Table
        dataSource={data?.items || []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize: 20,
          total: data?.total || 0,
          onChange: (p) => setPage(p),
          showSizeChanger: false,
          showTotal: (total) => `Total ${total} tasks`,
        }}
        scroll={{ x: 900 }}
      />
    </Card>
  );
}



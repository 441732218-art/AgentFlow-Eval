/* (c) 2026 AgentFlow-Eval */
/* 评测任务列表页 */

import React, { useEffect } from "react";
import { Button, Card, Space, Table, Tag, Popconfirm, message } from "antd";
import { PlusOutlined, PlayCircleOutlined, DeleteOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTaskStore } from "../../stores/useTaskStore";
import { formatDateTime, getStatusColor } from "../../utils/format";
import type { Task } from "../../types";
import Loading from "../../components/common/Loading";

const TaskList: React.FC = () => {
  const { tasks, total, loading, fetchTasks, deleteTask, executeTask } = useTaskStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const handleDelete = async (id: string) => {
    try {
      await deleteTask(id);
      message.success("任务已删除");
    } catch {
      message.error("删除失败");
    }
  };

  const handleExecute = async (id: string) => {
    try {
      await executeTask(id);
      message.success("任务已提交至执行队列");
    } catch {
      message.error("执行失败");
    }
  };

  const columns = [
    { title: "任务名称", dataIndex: "name", key: "name" },
    { title: "描述", dataIndex: "description", key: "description", ellipsis: true },
    { title: "状态", dataIndex: "status", key: "status",
      render: (s: string) => <Tag color={getStatusColor(s)}>{s}</Tag> },
    { title: "测试用例数", dataIndex: "test_suite_count", key: "test_suite_count" },
    { title: "创建时间", dataIndex: "created_at", key: "created_at",
      render: (v: string) => formatDateTime(v) },
    {
      title: "操作", key: "actions",
      render: (_: unknown, record: Task) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/tasks/${record.id}`)}>详情</Button>
          <Button type="link" icon={<PlayCircleOutlined />} onClick={() => handleExecute(record.id)} disabled={record.status === "running"}>执行</Button>
          <Popconfirm title="确认删除此任务?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) return <Loading />;

  return (
    <Card
      title="评测任务"
      extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/tasks/create")}>新建任务</Button>}
    >
      <Table
        dataSource={tasks}
        columns={columns}
        rowKey="id"
        pagination={{ total, pageSize: 20, showTotal: (t: number) => `共 ${t} 条` }}
      />
    </Card>
  );
};

export default TaskList;

/* (c) 2026 AgentFlow-Eval */
/* 总览面板 —— 统计卡片 + 近期任务列表 */

import React, { useEffect } from "react";
import { Card, Col, Row, Statistic, Table, Tag } from "antd";
import {
  ExperimentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useTaskStore } from "../../stores/useTaskStore";
import { formatDateTime, getStatusColor } from "../../utils/format";
import type { Task } from "../../types";
import Loading from "../../components/common/Loading";

const Dashboard: React.FC = () => {
  const { tasks, total, loading, fetchTasks } = useTaskStore();
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks(1);
  }, [fetchTasks]);

  const stats = {
    total,
    running: tasks.filter((t) => t.status === "running").length,
    completed: tasks.filter((t) => t.status === "completed").length,
    failed: tasks.filter((t) => t.status === "failed").length,
  };

  const columns = [
    { title: "任务名称", dataIndex: "name", key: "name" },
    { title: "状态", dataIndex: "status", key: "status",
      render: (s: string) => <Tag color={getStatusColor(s)}>{s}</Tag> },
    { title: "创建时间", dataIndex: "created_at", key: "created_at",
      render: (v: string) => formatDateTime(v) },
    { title: "测试用例数", dataIndex: "test_suite_count", key: "test_suite_count" },
  ];

  if (loading) return <Loading />;

  return (
    <>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="任务总数" value={stats.total} prefix={<ExperimentOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="运行中" value={stats.running} prefix={<ClockCircleOutlined />} valueStyle={{ color: "#1677ff" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已完成" value={stats.completed} prefix={<CheckCircleOutlined />} valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="失败" value={stats.failed} prefix={<CloseCircleOutlined />} valueStyle={{ color: "#ff4d4f" }} />
          </Card>
        </Col>
      </Row>

      <Card title="近期任务">
        <Table
          dataSource={tasks.slice(0, 10)}
          columns={columns}
          rowKey="id"
          pagination={false}
          onRow={(record: Task) => ({
            onClick: () => navigate(`/tasks/${record.id}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </>
  );
};

export default Dashboard;

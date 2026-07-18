/* (c) 2026 AgentFlow-Eval */
/* 顶部导航栏 */

import { Layout, Typography, Space } from "antd";
import { ExperimentOutlined } from "@ant-design/icons";

const { Header: AntHeader } = Layout;

const Header: React.FC = () => {
  return (
    <AntHeader
      style={{
        background: "#fff",
        padding: "0 24px",
        display: "flex",
        alignItems: "center",
        borderBottom: "1px solid #f0f0f0",
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: 64,
      }}
    >
      <Space>
        <ExperimentOutlined style={{ fontSize: 24, color: "#1677ff" }} />
        <Typography.Title level={4} style={{ margin: 0 }}>
          AgentFlow-Eval
        </Typography.Title>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          Agent 自动化评测工作台
        </Typography.Text>
      </Space>
    </AntHeader>
  );
};

export default Header;

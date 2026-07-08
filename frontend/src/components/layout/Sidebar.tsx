import React from "react";
import { Layout, Menu } from "antd";
import {
  UnorderedListOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";

const { Sider } = Layout;

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const menuItems = [
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "Tasks" },
  { key: "/tasks/create", icon: <PlusCircleOutlined />, label: "Create Task" },
  { key: "/reports", icon: <BarChartOutlined />, label: "Reports" },
  { key: "/settings", icon: <SettingOutlined />, label: "Settings" },
];

export const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onToggle}
      width={220}
      style={{
        background: "#fff",
        borderRight: "1px solid #f0f0f0",
      }}
    >
      <div
        style={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: "1px solid #f0f0f0",
        }}
      >
        <h2 style={{ margin: 0, fontSize: collapsed ? 14 : 18, fontWeight: 700, color: "#1677ff" }}>
          {collapsed ? "AE" : "AgentFlow-Eval"}
        </h2>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => navigate(key)}
        style={{ borderRight: 0, marginTop: 8 }}
      />
    </Sider>
  );
};

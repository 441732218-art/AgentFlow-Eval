/* (c) 2026 AgentFlow-Eval */
/* 侧边栏导航 */

import { useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  UnorderedListOutlined,
  PlusCircleOutlined,
} from "@ant-design/icons";

const { Sider } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "总览面板" },
  { key: "/tasks", icon: <UnorderedListOutlined />, label: "评测任务" },
  { key: "/tasks/create", icon: <PlusCircleOutlined />, label: "创建任务" },
];

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Sider
      width={220}
      style={{
        height: "100vh",
        position: "fixed",
        left: 0,
        top: 64,
        background: "#fff",
        borderRight: "1px solid #f0f0f0",
      }}
    >
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

export default Sidebar;

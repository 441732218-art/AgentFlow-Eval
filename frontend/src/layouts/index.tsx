/* (c) 2026 AgentFlow-Eval */
/* 主布局：侧边栏 + 内容区域 */

import { Outlet } from "react-router-dom";
import { Layout } from "antd";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

const { Content } = Layout;

const MainLayout: React.FC = () => {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header />
      <Layout style={{ marginTop: 64 }}>
        <Sidebar />
        <Content style={{ marginLeft: 220, padding: 24, background: "#f5f5f5" }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;

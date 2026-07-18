import React, { useEffect, useState } from "react";
import { Layout, Grid, Drawer } from "antd";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { CommandPalette } from "@/components/CommandPalette";
import { DocumentTitle } from "@/hooks/useDocumentTitle";
import { AppBreadcrumb } from "@/components/ui/AppBreadcrumb";
import { ActivityWatcher } from "@/components/layout/ActivityWatcher";
import { AIAssistant } from "@/components/realtime/AIAssistant";

const { Content } = Layout;
const { useBreakpoint } = Grid;

export const MainLayout: React.FC = () => {
  const screens = useBreakpoint();
  const isMobile = !screens.lg;
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
      setDrawerOpen(false);
    }
  }, [isMobile]);

  const toggleNav = () => {
    if (isMobile) setDrawerOpen((o) => !o);
    else setCollapsed((c) => !c);
  };

  return (
    <Layout
      className="af-layout ic-shell"
      style={{ minHeight: "100vh", background: "transparent" }}
    >
      <DocumentTitle />
      <ActivityWatcher />

      {!isMobile && (
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      )}

      <Drawer
        placement="left"
        open={isMobile && drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={260}
        styles={{
          body: { padding: 0, background: "var(--af-sidebar)" },
          header: { display: "none" },
        }}
        destroyOnClose={false}
      >
        <Sidebar
          collapsed={false}
          onToggle={() => setDrawerOpen(false)}
          mode="inline"
          onNavigate={() => setDrawerOpen(false)}
        />
      </Drawer>

      <Layout style={{ background: "transparent", minWidth: 0 }}>
        <Header collapsed={isMobile ? !drawerOpen : collapsed} onToggle={toggleNav} />
        <Content className="af-content-shell">
          <div className="ic-content-inner" style={{ minHeight: 280 }}>
            <AppBreadcrumb />
            <Outlet />
          </div>
        </Content>
      </Layout>
      <CommandPalette />
      <AIAssistant />
    </Layout>
  );
};

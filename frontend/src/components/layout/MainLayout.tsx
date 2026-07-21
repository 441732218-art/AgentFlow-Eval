import React, { useEffect, useState } from "react";
import { Layout, Grid, Drawer } from "antd";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { MobileBottomNav } from "./MobileBottomNav";
import { CommandPalette } from "@/components/CommandPalette";
import { DocumentTitle } from "@/hooks/useDocumentTitle";
import { AppBreadcrumb } from "@/components/ui/AppBreadcrumb";
import { ActivityWatcher } from "@/components/layout/ActivityWatcher";
import { AIAssistant } from "@/components/realtime/AIAssistant";
import { InstallPrompt } from "@/components/pwa/InstallPrompt";

const { Content } = Layout;
const { useBreakpoint } = Grid;

export const MainLayout: React.FC = () => {
  const screens = useBreakpoint();
  /** < lg (992): drawer nav; < md (768): also bottom tabs */
  const isMobile = !screens.lg;
  const isPhone = !screens.md;
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
      setDrawerOpen(false);
    }
  }, [isMobile]);

  useEffect(() => {
    document.body.classList.toggle("af-has-bottom-nav", isPhone);
    return () => document.body.classList.remove("af-has-bottom-nav");
  }, [isPhone]);

  useEffect(() => {
    const desktop = Boolean(
      (window as Window & { electronAPI?: unknown }).electronAPI
    );
    document.body.classList.toggle("af-desktop-shell", desktop);
  }, []);

  const toggleNav = () => {
    if (isMobile) setDrawerOpen((o) => !o);
    else setCollapsed((c) => !c);
  };

  return (
    <Layout
      className="af-layout ic-shell"
      style={{ minHeight: "100dvh", background: "transparent" }}
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
        width={Math.min(280, typeof window !== "undefined" ? window.innerWidth * 0.86 : 280)}
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

      <Layout style={{ background: "transparent", minWidth: 0, flex: 1 }}>
        <Header collapsed={isMobile ? !drawerOpen : collapsed} onToggle={toggleNav} />
        <Content className="af-content-shell">
          <div className="ic-content-inner" style={{ minHeight: 280 }}>
            {!isPhone && <AppBreadcrumb />}
            <Outlet />
          </div>
        </Content>
      </Layout>
      {isPhone && <MobileBottomNav />}
      <CommandPalette />
      <AIAssistant />
      <InstallPrompt />
    </Layout>
  );
};

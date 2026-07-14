import React from "react";
import { Layout, Menu, Typography } from "antd";
import { ExperimentOutlined } from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { NAV_ITEMS, resolveSelectedKey } from "./navItems";
import { useI18nStore } from "@/i18n";

const { Sider } = Layout;
const { Text } = Typography;

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  /** Desktop sticky sider only */
  mode?: "sider" | "inline";
  onNavigate?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggle,
  mode = "sider",
  onNavigate,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const selectedKey = resolveSelectedKey(location.pathname);
  const t = useI18nStore((s) => s.t);

  const brand = (
    <div
      style={{
        height: 64,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: collapsed && mode === "sider" ? "0 18px" : "0 20px",
        borderBottom: "1px solid var(--af-border)",
      }}
    >
      <div
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          background: "var(--af-gradient)",
          display: "grid",
          placeItems: "center",
          color: "#fff",
          flexShrink: 0,
          boxShadow: "var(--af-shadow-glow)",
        }}
      >
        <ExperimentOutlined style={{ fontSize: 16 }} />
      </div>
      {!(collapsed && mode === "sider") && (
        <div style={{ minWidth: 0 }}>
          <div
            className="af-gradient-text"
            style={{ fontWeight: 800, fontSize: 15, letterSpacing: "-0.02em", lineHeight: 1.2 }}
          >
            AgentFlow
          </div>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Eval Workbench
          </Text>
        </div>
      )}
    </div>
  );

  const menu = (
    <div style={{ padding: "12px 0 8px" }}>
      {!(collapsed && mode === "sider") && (
        <Text
          type="secondary"
          style={{
            fontSize: 11,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            padding: "0 20px 8px",
            display: "block",
          }}
        >
          Navigation
        </Text>
      )}
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={NAV_ITEMS.map((item) => ({
          key: item.key,
          icon: item.icon,
          label: t(item.labelKey),
        }))}
        onClick={({ key }) => {
          navigate(key);
          onNavigate?.();
        }}
        style={{ borderRight: 0, background: "transparent" }}
      />
    </div>
  );

  if (mode === "inline") {
    return (
      <div>
        {brand}
        {menu}
      </div>
    );
  }

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={onToggle}
      width={240}
      collapsedWidth={72}
      trigger={null}
      className="af-sider"
      style={{
        background: "var(--af-sidebar)",
        borderRight: "1px solid var(--af-border)",
        position: "sticky",
        top: 0,
        height: "100vh",
        zIndex: 20,
        display: "block",
      }}
    >
      {brand}
      {menu}
      {!collapsed && (
        <div
          style={{
            position: "absolute",
            bottom: 24,
            left: 12,
            right: 12,
            padding: 12,
            borderRadius: 12,
            background: "var(--af-gradient-soft)",
            border: "1px solid var(--af-border)",
          }}
        >
          <Text style={{ fontSize: 12, fontWeight: 600, display: "block", marginBottom: 4 }}>
            v0.1.0
          </Text>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Agent 自动化评测工作台
          </Text>
        </div>
      )}
    </Sider>
  );
};

import React, { useCallback, useMemo } from "react";
import { Layout, Menu } from "antd";
import type { MenuProps } from "antd";
import { useNavigate, useLocation } from "react-router-dom";
import { NAV_GROUPS, NAV_ITEMS, resolveSelectedKey } from "./navItems";
import { useI18nStore } from "@/i18n";
import { prefetchRoute, ROUTE_PREFETCH } from "@/lib/performance";
import { useAuth } from "@/auth";
import { BrandLogo } from "@/components/brand/BrandLogo";

const { Sider } = Layout;

const PREFETCH_BY_KEY: Record<string, () => Promise<unknown>> = {
  "/dashboard": ROUTE_PREFETCH.dashboard,
  "/traces": ROUTE_PREFETCH.traces,
  "/diagnosis": ROUTE_PREFETCH.diagnosis,
  "/analytics": ROUTE_PREFETCH.analytics,
  "/monitoring": ROUTE_PREFETCH.monitoring,
  "/tasks": ROUTE_PREFETCH.tasks,
  "/tasks/create": ROUTE_PREFETCH.createTask,
  "/reports": ROUTE_PREFETCH.reports,
  "/billing": ROUTE_PREFETCH.billing,
  "/plugins": ROUTE_PREFETCH.plugins,
  "/settings": ROUTE_PREFETCH.settings,
};

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
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
  const locale = useI18nStore((s) => s.locale);
  const { can, rbacEnforced } = useAuth();

  const onPrefetch = useCallback((key: string) => {
    const loader = PREFETCH_BY_KEY[key];
    if (loader) prefetchRoute(loader);
  }, []);

  const menuItems: MenuProps["items"] = useMemo(() => {
    const visible = NAV_ITEMS.filter(
      (item) => !rbacEnforced || !item.permission || can(item.permission)
    );

    const hideGroupTitle = collapsed && mode === "sider";
    const result: NonNullable<MenuProps["items"]> = [];

    for (const group of NAV_GROUPS) {
      const children = visible
        .filter((item) => item.group === group.id)
        .map((item) => ({
          key: item.key,
          icon: item.icon,
          label: (
            <span
              onMouseEnter={() => onPrefetch(item.key)}
              onFocus={() => onPrefetch(item.key)}
            >
              {t(item.labelKey)}
            </span>
          ),
        }));

      if (!children.length) continue;

      if (hideGroupTitle) {
        result.push(...children);
      } else {
        result.push({
          type: "group",
          key: `grp-${group.id}`,
          label: locale === "en" ? group.labelEn : group.label,
          children,
        });
      }
    }

    return result;
  }, [t, onPrefetch, can, rbacEnforced, collapsed, mode, locale]);

  const brand = (
    <div
      className="ic-sider-brand"
      style={{
        height: 64,
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: collapsed && mode === "sider" ? "0 18px" : "0 16px",
        borderBottom: "1px solid var(--af-border)",
        cursor: "pointer",
      }}
      onClick={() => navigate("/dashboard")}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") navigate("/dashboard");
      }}
    >
      {collapsed && mode === "sider" ? (
        <BrandLogo variant="mark" size={34} />
      ) : (
        <BrandLogo variant="lockup" size={34} />
      )}
    </div>
  );

  const menu = (
    <div style={{ padding: "8px 0 80px" }}>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={({ key }) => {
          if (String(key).startsWith("grp-")) return;
          navigate(key);
          onNavigate?.();
        }}
        style={{ borderRight: 0, background: "transparent" }}
      />
    </div>
  );

  if (mode === "inline") {
    return (
      <div className="ic-sider ic-sider--inline">
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
      width={248}
      collapsedWidth={72}
      trigger={null}
      className="af-sider ic-sider"
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
        <div className="ic-sider-footer">
          <span className="ic-sider-footer__ver">AgentFlow Intelligence</span>
          <span className="ic-sider-footer__hint">
            Observability · Evaluation · Diagnosis
          </span>
        </div>
      )}
    </Sider>
  );
};

/* Mobile bottom navigation — primary destinations under 768px */

import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  DashboardOutlined,
  UnorderedListOutlined,
  ApartmentOutlined,
  BugOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { useI18nStore } from "@/i18n";
import { useAuth } from "@/auth";

type Tab = {
  key: string;
  match: (path: string) => boolean;
  icon: React.ReactNode;
  labelKey: "nav.dashboard" | "nav.tasks" | "nav.traces" | "nav.diagnosis" | "nav.settings";
  permission?: string;
};

const TABS: Tab[] = [
  {
    key: "/dashboard",
    match: (p) => p === "/" || p.startsWith("/dashboard"),
    icon: <DashboardOutlined />,
    labelKey: "nav.dashboard",
    permission: "task:read",
  },
  {
    key: "/tasks",
    match: (p) => p.startsWith("/tasks"),
    icon: <UnorderedListOutlined />,
    labelKey: "nav.tasks",
    permission: "task:read",
  },
  {
    key: "/traces",
    match: (p) => p.startsWith("/traces"),
    icon: <ApartmentOutlined />,
    labelKey: "nav.traces",
    permission: "evaluation:read",
  },
  {
    key: "/diagnosis",
    match: (p) => p.startsWith("/diagnosis"),
    icon: <BugOutlined />,
    labelKey: "nav.diagnosis",
    permission: "evaluation:read",
  },
  {
    key: "/settings",
    match: (p) => p.startsWith("/settings"),
    icon: <SettingOutlined />,
    labelKey: "nav.settings",
  },
];

export function MobileBottomNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const t = useI18nStore((s) => s.t);
  const { can, rbacEnforced } = useAuth();

  const items = useMemo(
    () =>
      TABS.filter((tab) => !rbacEnforced || !tab.permission || can(tab.permission as never)),
    [can, rbacEnforced]
  );

  if (!items.length) return null;

  return (
    <nav className="af-mobile-bottom-nav af-no-print" aria-label="Primary">
      {items.map((tab) => {
        const active = tab.match(pathname);
        return (
          <button
            key={tab.key}
            type="button"
            className={`af-mobile-bottom-nav__item${active ? " is-active" : ""}`}
            aria-current={active ? "page" : undefined}
            onClick={() => navigate(tab.key)}
          >
            {tab.icon}
            <span className="af-mobile-bottom-nav__label">{t(tab.labelKey)}</span>
          </button>
        );
      })}
    </nav>
  );
}

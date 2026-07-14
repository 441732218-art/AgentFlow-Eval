import {
  DashboardOutlined,
  UnorderedListOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import type { MessageKey } from "@/i18n";

export const NAV_ITEMS: Array<{
  key: string;
  icon: React.ReactNode;
  labelKey: MessageKey;
  label: string;
}> = [
  { key: "/", icon: <DashboardOutlined />, labelKey: "nav.dashboard", label: "总览" },
  { key: "/tasks", icon: <UnorderedListOutlined />, labelKey: "nav.tasks", label: "任务" },
  { key: "/tasks/create", icon: <PlusCircleOutlined />, labelKey: "nav.create", label: "创建任务" },
  { key: "/reports", icon: <BarChartOutlined />, labelKey: "nav.reports", label: "报告" },
  { key: "/settings", icon: <SettingOutlined />, labelKey: "nav.settings", label: "设置" },
];

export function resolveSelectedKey(pathname: string): string {
  if (pathname === "/") return "/";
  if (pathname.startsWith("/reports")) return "/reports";
  if (pathname === "/tasks/create") return "/tasks/create";
  if (pathname.startsWith("/tasks")) return "/tasks";
  if (pathname.startsWith("/settings")) return "/settings";
  return pathname;
}

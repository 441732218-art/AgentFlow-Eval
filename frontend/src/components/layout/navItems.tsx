import {
  DashboardOutlined,
  UnorderedListOutlined,
  PlusCircleOutlined,
  BarChartOutlined,
  SettingOutlined,
  AccountBookOutlined,
  AppstoreOutlined,
  ApartmentOutlined,
  BugOutlined,
  FundProjectionScreenOutlined,
  CloudServerOutlined,
} from "@ant-design/icons";
import type { MessageKey } from "@/i18n";
import type { Permission } from "@/auth/permissions";

export type NavGroupId = "command" | "evaluate" | "operate" | "system";

export const NAV_GROUPS: Array<{ id: NavGroupId; label: string; labelEn: string }> = [
  { id: "command", label: "Command", labelEn: "Command" },
  { id: "evaluate", label: "Evaluate", labelEn: "Evaluate" },
  { id: "operate", label: "Operate", labelEn: "Operate" },
  { id: "system", label: "System", labelEn: "System" },
];

export const NAV_ITEMS: Array<{
  key: string;
  icon: React.ReactNode;
  labelKey: MessageKey;
  label: string;
  permission?: Permission;
  group: NavGroupId;
}> = [
  {
    key: "/dashboard",
    icon: <DashboardOutlined />,
    labelKey: "nav.dashboard",
    label: "驾驶舱",
    permission: "task:read",
    group: "command",
  },
  {
    key: "/traces",
    icon: <ApartmentOutlined />,
    labelKey: "nav.traces",
    label: "Trace",
    permission: "evaluation:read",
    group: "command",
  },
  {
    key: "/diagnosis",
    icon: <BugOutlined />,
    labelKey: "nav.diagnosis",
    label: "故障诊断",
    permission: "evaluation:read",
    group: "command",
  },
  {
    key: "/analytics",
    icon: <FundProjectionScreenOutlined />,
    labelKey: "nav.analytics",
    label: "分析",
    permission: "evaluation:read",
    group: "command",
  },
  {
    key: "/monitoring",
    icon: <CloudServerOutlined />,
    labelKey: "nav.monitoring",
    label: "监控",
    permission: "task:read",
    group: "command",
  },
  {
    key: "/tasks",
    icon: <UnorderedListOutlined />,
    labelKey: "nav.tasks",
    label: "任务",
    permission: "task:read",
    group: "evaluate",
  },
  {
    key: "/tasks/create",
    icon: <PlusCircleOutlined />,
    labelKey: "nav.create",
    label: "创建任务",
    permission: "task:create",
    group: "evaluate",
  },
  {
    key: "/reports",
    icon: <BarChartOutlined />,
    labelKey: "nav.reports",
    label: "报告",
    permission: "evaluation:read",
    group: "evaluate",
  },
  {
    key: "/benchmarks",
    icon: <BarChartOutlined />,
    labelKey: "nav.benchmarks",
    label: "Benchmark",
    permission: "benchmark:read",
    group: "evaluate",
  },
  {
    key: "/billing",
    icon: <AccountBookOutlined />,
    labelKey: "nav.billing",
    label: "用量计费",
    permission: "task:read",
    group: "operate",
  },
  {
    key: "/plugins",
    icon: <AppstoreOutlined />,
    labelKey: "nav.plugins",
    label: "插件市场",
    permission: "system:config",
    group: "operate",
  },
  {
    key: "/settings",
    icon: <SettingOutlined />,
    labelKey: "nav.settings",
    label: "设置",
    permission: "system:config",
    group: "system",
  },
];

export function resolveSelectedKey(pathname: string): string {
  if (pathname === "/" || pathname.startsWith("/dashboard")) return "/dashboard";
  if (pathname.startsWith("/traces")) return "/traces";
  if (pathname.startsWith("/diagnosis")) return "/diagnosis";
  if (pathname.startsWith("/analytics")) return "/analytics";
  if (pathname.startsWith("/monitoring")) return "/monitoring";
  if (pathname.startsWith("/reports")) return "/reports";
  if (pathname.startsWith("/benchmarks")) return "/benchmarks";
  if (pathname === "/tasks/create") return "/tasks/create";
  if (pathname.startsWith("/tasks")) return "/tasks";
  if (pathname.startsWith("/billing")) return "/billing";
  if (pathname.startsWith("/plugins")) return "/plugins";
  if (pathname.startsWith("/settings")) return "/settings";
  return pathname;
}

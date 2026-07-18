import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const TITLE_MAP: Array<{ match: RegExp | string; title: string }> = [
  { match: /^\/$/, title: "驾驶舱" },
  { match: /^\/dashboard$/, title: "AI 驾驶舱" },
  { match: /^\/traces$/, title: "Trace Explorer" },
  { match: /^\/diagnosis$/, title: "故障诊断" },
  { match: /^\/analytics$/, title: "分析中心" },
  { match: /^\/monitoring$/, title: "实时监控" },
  { match: /^\/tasks\/create$/, title: "创建任务" },
  { match: /^\/tasks\/[^/]+$/, title: "任务详情" },
  { match: /^\/tasks$/, title: "任务列表" },
  { match: /^\/reports\/[^/]+$/, title: "评测报告" },
  { match: /^\/reports$/, title: "报告中心" },
  { match: /^\/billing$/, title: "用量计费" },
  { match: /^\/plugins$/, title: "插件市场" },
  { match: /^\/settings$/, title: "设置" },
  { match: /^\/404$/, title: "页面未找到" },
];

const APP_NAME = "AgentFlow Intelligence";

/** Browser title product name (keep in sync with index.html) */
export const PRODUCT_NAME = APP_NAME;

export function resolvePageTitle(pathname: string): string {
  for (const item of TITLE_MAP) {
    if (typeof item.match === "string" ? pathname === item.match : item.match.test(pathname)) {
      return `${item.title} · ${APP_NAME}`;
    }
  }
  return APP_NAME;
}

/** Call inside router tree to keep document.title in sync. */
export function useDocumentTitle(override?: string) {
  const { pathname } = useLocation();
  useEffect(() => {
    document.title = override || resolvePageTitle(pathname);
  }, [pathname, override]);
}

export function DocumentTitle() {
  useDocumentTitle();
  return null;
}

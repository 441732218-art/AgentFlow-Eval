/* Lightweight i18n — zh / en with localStorage persistence */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Locale = "zh" | "en";

const dict = {
  zh: {
    "nav.dashboard": "总览",
    "nav.tasks": "任务",
    "nav.create": "创建任务",
    "nav.reports": "报告",
    "nav.settings": "设置",
    "header.search": "搜索页面 / 任务 / 操作…",
    "header.notify": "活动通知",
    "header.theme.dark": "切换亮色",
    "header.theme.light": "切换深色",
    "header.workspace": "工作区",
    "notify.title": "活动通知",
    "notify.active": "进行中",
    "notify.empty": "暂无活动",
    "notify.allTasks": "查看全部任务",
    "notify.markAll": "全部已读",
    "notify.clear": "清空",
    "notify.live": "轮询同步",
    "notify.ws": "WebSocket 实时",
    "tasks.create": "创建任务",
    "tasks.search": "搜索任务名称、描述、Owner…",
    "tasks.empty": "没有匹配的任务",
    "tasks.view.card": "卡片",
    "tasks.view.table": "列表",
    "tasks.status.all": "全部状态",
    "create.title": "创建评测任务",
    "create.subtitle": "配置 Agent 模型与参数，创建后可导入用例并执行流水线",
    "create.submit": "创建任务",
    "create.sample": "填充示例",
    "create.back": "返回列表",
    "create.cancel": "取消",
    "reports.empty": "暂无报告",
    "reports.emptyDesc": "完成评测任务后，终态结果会出现在这里。",
    "reports.view": "查看",
    "common.delete": "删除",
    "common.detail": "详情",
    "common.execute": "执行",
    "common.report": "报告",
    "dashboard.title": "工作台总览",
    "dashboard.subtitle": "实时掌握评测任务分布与近期活动",
    "dashboard.create": "创建任务",
    "dashboard.total": "任务总数",
    "dashboard.running": "运行中",
    "dashboard.completed": "已完成",
    "dashboard.failed": "失败",
    "dashboard.rate": "完成率",
    "dashboard.statusDist": "状态分布",
    "dashboard.trend": "创建趋势",
    "dashboard.recent": "近期任务",
    "dashboard.allTasks": "全部任务",
    "dashboard.noData": "暂无数据",
    "dashboard.noTasks": "暂无任务",
    "dashboard.clickHint": "点击下钻到任务列表",
    "tasks.title": "评测任务",
    "tasks.subtitle": "管理与执行 Agent 评测流水线",
    "reports.title": "评测报告",
    "reports.subtitle": "查看终态任务的汇总评分与导出入口",
    "settings.title": "系统设置",
    "settings.language": "界面语言",
    "settings.lang.zh": "中文",
    "settings.lang.en": "English",
    "common.retry": "重试",
    "common.refresh": "刷新",
    "common.loading": "加载中…",
    "cmd.placeholder": "搜索页面、任务、报告或操作…",
    "cmd.help": "快捷键",
    "cmd.empty": "无匹配结果",
  },
  en: {
    "nav.dashboard": "Dashboard",
    "nav.tasks": "Tasks",
    "nav.create": "Create task",
    "nav.reports": "Reports",
    "nav.settings": "Settings",
    "header.search": "Search pages / tasks / actions…",
    "header.notify": "Activity",
    "header.theme.dark": "Switch to light",
    "header.theme.light": "Switch to dark",
    "header.workspace": "Workspace",
    "notify.title": "Activity",
    "notify.active": "In progress",
    "notify.empty": "No activity yet",
    "notify.allTasks": "View all tasks",
    "notify.markAll": "Mark all read",
    "notify.clear": "Clear",
    "notify.live": "Polling sync",
    "notify.ws": "WebSocket live",
    "tasks.create": "New task",
    "tasks.search": "Search name, description, owner…",
    "tasks.empty": "No matching tasks",
    "tasks.view.card": "Cards",
    "tasks.view.table": "Table",
    "tasks.status.all": "All statuses",
    "create.title": "Create evaluation task",
    "create.subtitle": "Configure the agent model, then import suites and run",
    "create.submit": "Create task",
    "create.sample": "Fill sample",
    "create.back": "Back to list",
    "create.cancel": "Cancel",
    "reports.empty": "No reports yet",
    "reports.emptyDesc": "Finished evaluation tasks will appear here.",
    "reports.view": "View",
    "common.delete": "Delete",
    "common.detail": "Details",
    "common.execute": "Run",
    "common.report": "Report",
    "dashboard.title": "Workspace overview",
    "dashboard.subtitle": "Live distribution of evaluation tasks and recent activity",
    "dashboard.create": "New task",
    "dashboard.total": "Total tasks",
    "dashboard.running": "Running",
    "dashboard.completed": "Completed",
    "dashboard.failed": "Failed",
    "dashboard.rate": "Completion rate",
    "dashboard.statusDist": "Status distribution",
    "dashboard.trend": "Creation trend",
    "dashboard.recent": "Recent tasks",
    "dashboard.allTasks": "All tasks",
    "dashboard.noData": "No data",
    "dashboard.noTasks": "No tasks yet",
    "dashboard.clickHint": "Click to drill into task list",
    "tasks.title": "Evaluation tasks",
    "tasks.subtitle": "Manage and run Agent evaluation pipelines",
    "reports.title": "Evaluation reports",
    "reports.subtitle": "Scores and export for finished tasks",
    "settings.title": "Settings",
    "settings.language": "Language",
    "settings.lang.zh": "中文",
    "settings.lang.en": "English",
    "common.retry": "Retry",
    "common.refresh": "Refresh",
    "common.loading": "Loading…",
    "cmd.placeholder": "Search pages, tasks, reports or actions…",
    "cmd.help": "Shortcuts",
    "cmd.empty": "No matches",
  },
} as const;

export type MessageKey = keyof (typeof dict)["zh"];

interface I18nState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey, fallback?: string) => string;
}

export const useI18nStore = create<I18nState>()(
  persist(
    (set, get) => ({
      locale: "zh",
      setLocale: (locale) => {
        set({ locale });
        document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
      },
      t: (key, fallback) => {
        const loc = get().locale;
        return dict[loc][key] ?? dict.zh[key] ?? fallback ?? key;
      },
    }),
    { name: "agentflow_locale" }
  )
);

export function t(key: MessageKey, fallback?: string): string {
  return useI18nStore.getState().t(key, fallback);
}

// Apply lang attribute early
try {
  const raw = localStorage.getItem("agentflow_locale");
  if (raw) {
    const parsed = JSON.parse(raw) as { state?: { locale?: Locale } };
    const loc = parsed.state?.locale;
    if (loc === "en" || loc === "zh") {
      document.documentElement.lang = loc === "zh" ? "zh-CN" : "en";
    }
  }
} catch {
  /* ignore */
}

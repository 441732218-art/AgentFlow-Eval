/* (c) 2026 AgentFlow-Eval */

import React, { useMemo } from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { useThemeStore } from "@/stores/useThemeStore";
import { buildAntdTheme } from "@/theme/antdTheme";
import "@/styles/theme.css";
import "@/styles/command-center.css";
import "@/styles/responsive.css";

// Apply theme before first paint (avoid flash) — Cyber Command default
try {
  const known = new Set([
    "dark",
    "light",
    "midnight",
    "emerald",
    "ocean",
    "sunset",
  ]);
  const saved =
    localStorage.getItem("agentflow_theme_v3") ||
    localStorage.getItem("agentflow_theme_v2");
  document.documentElement.setAttribute(
    "data-theme",
    saved && known.has(saved) ? saved : "dark"
  );
} catch {
  document.documentElement.setAttribute("data-theme", "dark");
}

function Root() {
  const mode = useThemeStore((s) => s.mode);
  const theme = useMemo(() => buildAntdTheme(mode), [mode]);

  return (
    <ConfigProvider locale={zhCN} theme={theme}>
      <AntApp>
        <App />
      </AntApp>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

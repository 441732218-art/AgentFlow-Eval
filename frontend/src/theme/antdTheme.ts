import type { ThemeConfig } from "antd";
import { theme as antTheme } from "antd";
import type { ThemeMode } from "@/stores/useThemeStore";
import { isDarkTheme } from "@/stores/useThemeStore";

type Palette = {
  colorPrimary: string;
  colorInfo: string;
  colorSuccess: string;
  colorWarning: string;
  colorError: string;
  colorBgBase: string;
  colorBgContainer: string;
  colorBgElevated: string;
  colorBorder: string;
  colorBorderSecondary: string;
  colorText: string;
  colorTextSecondary: string;
  headerBg: string;
  tableHeaderBg: string;
  rowHoverBg: string;
  itemHoverBg: string;
  itemSelectedColor: string;
  primaryShadow: string;
  activeBorder: string;
  hoverBorder: string;
  boxShadow: string;
};

const palettes: Record<ThemeMode, Palette> = {
  dark: {
    colorPrimary: "#38bdf8",
    colorInfo: "#818cf8",
    colorSuccess: "#34d399",
    colorWarning: "#fbbf24",
    colorError: "#f87171",
    colorBgBase: "#07090f",
    colorBgContainer: "#121826",
    colorBgElevated: "#1a2234",
    colorBorder: "rgba(148,163,184,0.14)",
    colorBorderSecondary: "rgba(148,163,184,0.1)",
    colorText: "#e8eef9",
    colorTextSecondary: "#94a3b8",
    headerBg: "#0c101a",
    tableHeaderBg: "#0c101a",
    rowHoverBg: "rgba(56,189,248,0.06)",
    itemHoverBg: "rgba(56,189,248,0.08)",
    itemSelectedColor: "#38bdf8",
    primaryShadow: "0 4px 14px rgba(56, 189, 248, 0.25)",
    activeBorder: "#38bdf8",
    hoverBorder: "#7dd3fc",
    boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
  },
  midnight: {
    colorPrimary: "#a78bfa",
    colorInfo: "#c084fc",
    colorSuccess: "#34d399",
    colorWarning: "#fbbf24",
    colorError: "#f472b6",
    colorBgBase: "#0b0714",
    colorBgContainer: "#151022",
    colorBgElevated: "#1e1630",
    colorBorder: "rgba(167,139,250,0.16)",
    colorBorderSecondary: "rgba(167,139,250,0.1)",
    colorText: "#f0e9ff",
    colorTextSecondary: "#a89bc8",
    headerBg: "#100c1c",
    tableHeaderBg: "#100c1c",
    rowHoverBg: "rgba(167,139,250,0.08)",
    itemHoverBg: "rgba(167,139,250,0.1)",
    itemSelectedColor: "#a78bfa",
    primaryShadow: "0 4px 14px rgba(167, 139, 250, 0.28)",
    activeBorder: "#a78bfa",
    hoverBorder: "#c4b5fd",
    boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
  },
  emerald: {
    colorPrimary: "#34d399",
    colorInfo: "#2dd4bf",
    colorSuccess: "#4ade80",
    colorWarning: "#fbbf24",
    colorError: "#f87171",
    colorBgBase: "#050d0a",
    colorBgContainer: "#0c1814",
    colorBgElevated: "#142420",
    colorBorder: "rgba(52,211,153,0.14)",
    colorBorderSecondary: "rgba(52,211,153,0.1)",
    colorText: "#e6f7f0",
    colorTextSecondary: "#8aaba0",
    headerBg: "#0a1411",
    tableHeaderBg: "#0a1411",
    rowHoverBg: "rgba(52,211,153,0.07)",
    itemHoverBg: "rgba(52,211,153,0.09)",
    itemSelectedColor: "#34d399",
    primaryShadow: "0 4px 14px rgba(52, 211, 153, 0.25)",
    activeBorder: "#34d399",
    hoverBorder: "#6ee7b7",
    boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
  },
  ocean: {
    colorPrimary: "#22d3ee",
    colorInfo: "#38bdf8",
    colorSuccess: "#34d399",
    colorWarning: "#fbbf24",
    colorError: "#f87171",
    colorBgBase: "#040b12",
    colorBgContainer: "#0a1520",
    colorBgElevated: "#122030",
    colorBorder: "rgba(34,211,238,0.14)",
    colorBorderSecondary: "rgba(34,211,238,0.1)",
    colorText: "#e6f4fa",
    colorTextSecondary: "#7fa3b5",
    headerBg: "#081018",
    tableHeaderBg: "#081018",
    rowHoverBg: "rgba(34,211,238,0.07)",
    itemHoverBg: "rgba(34,211,238,0.09)",
    itemSelectedColor: "#22d3ee",
    primaryShadow: "0 4px 14px rgba(34, 211, 238, 0.25)",
    activeBorder: "#22d3ee",
    hoverBorder: "#67e8f9",
    boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
  },
  sunset: {
    colorPrimary: "#fb923c",
    colorInfo: "#f472b6",
    colorSuccess: "#34d399",
    colorWarning: "#fbbf24",
    colorError: "#f87171",
    colorBgBase: "#0f0806",
    colorBgContainer: "#1a100c",
    colorBgElevated: "#261812",
    colorBorder: "rgba(251,146,60,0.16)",
    colorBorderSecondary: "rgba(251,146,60,0.1)",
    colorText: "#faf0e8",
    colorTextSecondary: "#b8a090",
    headerBg: "#140c09",
    tableHeaderBg: "#140c09",
    rowHoverBg: "rgba(251,146,60,0.07)",
    itemHoverBg: "rgba(251,146,60,0.09)",
    itemSelectedColor: "#fb923c",
    primaryShadow: "0 4px 14px rgba(251, 146, 60, 0.28)",
    activeBorder: "#fb923c",
    hoverBorder: "#fdba74",
    boxShadow: "0 8px 24px rgba(0,0,0,0.38)",
  },
  light: {
    colorPrimary: "#0284c7",
    colorInfo: "#4f46e5",
    colorSuccess: "#059669",
    colorWarning: "#d97706",
    colorError: "#dc2626",
    colorBgBase: "#f4f6fb",
    colorBgContainer: "#ffffff",
    colorBgElevated: "#ffffff",
    colorBorder: "rgba(15,23,42,0.08)",
    colorBorderSecondary: "rgba(15,23,42,0.06)",
    colorText: "#0f172a",
    colorTextSecondary: "#475569",
    headerBg: "#f8fafc",
    tableHeaderBg: "#f8fafc",
    rowHoverBg: "rgba(2,132,199,0.04)",
    itemHoverBg: "rgba(2,132,199,0.06)",
    itemSelectedColor: "#0284c7",
    primaryShadow: "0 4px 14px rgba(2, 132, 199, 0.18)",
    activeBorder: "#0284c7",
    hoverBorder: "#38bdf8",
    boxShadow: "0 8px 24px rgba(15,23,42,0.08)",
  },
};

export function buildAntdTheme(mode: ThemeMode): ThemeConfig {
  const dark = isDarkTheme(mode);
  const p = palettes[mode] ?? palettes.dark;

  return {
    algorithm: dark ? antTheme.darkAlgorithm : antTheme.defaultAlgorithm,
    token: {
      colorPrimary: p.colorPrimary,
      colorInfo: p.colorInfo,
      colorSuccess: p.colorSuccess,
      colorWarning: p.colorWarning,
      colorError: p.colorError,
      colorBgBase: p.colorBgBase,
      colorBgContainer: p.colorBgContainer,
      colorBgElevated: p.colorBgElevated,
      colorBorder: p.colorBorder,
      colorBorderSecondary: p.colorBorderSecondary,
      colorText: p.colorText,
      colorTextSecondary: p.colorTextSecondary,
      borderRadius: 10,
      borderRadiusLG: 14,
      fontFamily:
        '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
      fontSize: 14,
      controlHeight: 38,
      boxShadow: p.boxShadow,
      wireframe: false,
    },
    components: {
      Layout: {
        bodyBg: "transparent",
        headerBg: "transparent",
        siderBg: "transparent",
        triggerBg: p.colorBgElevated,
      },
      Card: {
        colorBgContainer: p.colorBgContainer,
        paddingLG: 20,
      },
      Menu: {
        itemBg: "transparent",
        subMenuItemBg: "transparent",
        itemSelectedColor: p.itemSelectedColor,
        itemHoverBg: p.itemHoverBg,
      },
      Button: {
        primaryShadow: p.primaryShadow,
        borderRadius: 10,
      },
      Input: {
        activeBorderColor: p.activeBorder,
        hoverBorderColor: p.hoverBorder,
      },
      Tag: {
        borderRadiusSM: 6,
      },
      Table: {
        headerBg: p.tableHeaderBg,
        rowHoverBg: p.rowHoverBg,
      },
      Modal: {
        contentBg: p.colorBgContainer,
        headerBg: p.colorBgContainer,
      },
    },
  };
}

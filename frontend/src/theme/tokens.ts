/**
 * AgentFlow Intelligence Center — Design Tokens (single source of truth)
 *
 * CSS variables in theme.css / command-center.css must stay in sync with
 * COMMAND_PALETTE and buildAntdTheme(). Prefer importing from here in TS.
 */

export const COMMAND_PALETTE = {
  bg: "#050816",
  bgElevated: "#0a1024",
  bgSurface: "#0d152e",
  bgMuted: "#121c3a",
  bgHover: "#1a2748",
  primary: "#00D4FF",
  accent: "#8B5CF6",
  success: "#00FF9D",
  warning: "#FFC857",
  danger: "#FF3864",
  text: "#e8f4ff",
  textSecondary: "#8ba3c7",
  textMuted: "#5a7399",
  border: "rgba(0, 212, 255, 0.14)",
  borderStrong: "rgba(0, 212, 255, 0.28)",
  sidebar: "#070c1a",
  header: "rgba(7, 12, 26, 0.88)",
  panel: "rgba(10, 16, 36, 0.88)",
  glow: "0 0 24px rgba(0, 212, 255, 0.25)",
} as const;

export const RADIUS = {
  sm: 8,
  md: 12,
  lg: 14,
  xl: 20,
} as const;

export const FONT = {
  sans: '"Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
  mono: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
} as const;

/** Status tone → CSS color (for badges, flow nodes, charts) */
export const STATUS_TONE = {
  ok: COMMAND_PALETTE.success,
  success: COMMAND_PALETTE.success,
  warn: COMMAND_PALETTE.warning,
  warning: COMMAND_PALETTE.warning,
  error: COMMAND_PALETTE.danger,
  danger: COMMAND_PALETTE.danger,
  idle: COMMAND_PALETTE.textMuted,
  info: COMMAND_PALETTE.primary,
  purple: COMMAND_PALETTE.accent,
} as const;

export type StatusTone = keyof typeof STATUS_TONE;

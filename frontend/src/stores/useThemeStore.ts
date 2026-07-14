import { create } from "zustand";

/** Available UI color themes */
export type ThemeMode =
  | "dark"
  | "light"
  | "midnight"
  | "emerald"
  | "ocean"
  | "sunset";

export const THEME_OPTIONS: ReadonlyArray<{
  value: ThemeMode;
  label: string;
  labelEn: string;
  /** Whether Ant Design / OS should treat this as a dark scheme */
  isDark: boolean;
  /** Swatch color for option previews */
  swatch: string;
}> = [
  {
    value: "dark",
    label: "深空暗色（推荐）",
    labelEn: "Deep Space Dark",
    isDark: true,
    swatch: "#38bdf8",
  },
  {
    value: "midnight",
    label: "午夜紫",
    labelEn: "Midnight Violet",
    isDark: true,
    swatch: "#a78bfa",
  },
  {
    value: "emerald",
    label: "翡翠绿",
    labelEn: "Emerald Night",
    isDark: true,
    swatch: "#34d399",
  },
  {
    value: "ocean",
    label: "深海蓝",
    labelEn: "Deep Ocean",
    isDark: true,
    swatch: "#22d3ee",
  },
  {
    value: "sunset",
    label: "落日暖橙",
    labelEn: "Sunset Warm",
    isDark: true,
    swatch: "#fb923c",
  },
  {
    value: "light",
    label: "明亮浅色",
    labelEn: "Bright Light",
    isDark: false,
    swatch: "#0284c7",
  },
] as const;

export const THEME_MODE_SET = new Set<string>(THEME_OPTIONS.map((o) => o.value));

export function isThemeMode(v: string | null | undefined): v is ThemeMode {
  return !!v && THEME_MODE_SET.has(v);
}

export function isDarkTheme(mode: ThemeMode): boolean {
  return THEME_OPTIONS.find((o) => o.value === mode)?.isDark ?? true;
}

const STORAGE_KEY = "agentflow_theme";
const LAST_DARK_KEY = "agentflow_theme_last_dark";

function readInitial(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (isThemeMode(v)) return v;
  } catch {
    /* ignore */
  }
  if (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: light)").matches
  ) {
    return "light";
  }
  return "dark";
}

function readLastDark(): ThemeMode {
  try {
    const v = localStorage.getItem(LAST_DARK_KEY);
    if (isThemeMode(v) && isDarkTheme(v)) return v;
  } catch {
    /* ignore */
  }
  return "dark";
}

function applyDom(mode: ThemeMode) {
  document.documentElement.setAttribute("data-theme", mode);
}

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  /** Quick toggle between light and the last dark palette */
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => {
  const initial = typeof document !== "undefined" ? readInitial() : "dark";
  if (typeof document !== "undefined") applyDom(initial);

  return {
    mode: initial,
    setMode: (mode) => {
      localStorage.setItem(STORAGE_KEY, mode);
      if (isDarkTheme(mode)) {
        try {
          localStorage.setItem(LAST_DARK_KEY, mode);
        } catch {
          /* ignore */
        }
      }
      applyDom(mode);
      set({ mode });
    },
    toggle: () => {
      const current = get().mode;
      if (isDarkTheme(current)) {
        get().setMode("light");
      } else {
        get().setMode(readLastDark());
      }
    },
  };
});

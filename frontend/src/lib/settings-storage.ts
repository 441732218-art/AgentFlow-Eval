/* (c) 2026 AgentFlow-Eval */
/** Shared local settings + API key helpers (single source of truth). */

export const SETTINGS_KEY = "agentflow_settings";

export type LocalSettings = {
  apiBaseUrl: string;
  apiKey: string;
  pollIntervalSec: number;
  showArchived: boolean;
  preferredActorLabel: string;
};

export const defaultSettings = (): LocalSettings => ({
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  apiKey: "",
  pollIntervalSec: 3,
  showArchived: false,
  preferredActorLabel: "",
});

export function loadSettings(): LocalSettings {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return defaultSettings();
    return { ...defaultSettings(), ...JSON.parse(raw) };
  } catch {
    return defaultSettings();
  }
}

export function saveSettings(partial: Partial<LocalSettings>): LocalSettings {
  const next = { ...loadSettings(), ...partial };
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
  return next;
}

export function readLocalApiKey(): string {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw) as { apiKey?: string };
    return (parsed.apiKey || "").trim();
  } catch {
    return "";
  }
}

export function writeLocalApiKey(apiKey: string): void {
  saveSettings({ apiKey: (apiKey || "").trim() });
}

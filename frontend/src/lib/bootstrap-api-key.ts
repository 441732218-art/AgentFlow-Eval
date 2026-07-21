/* (c) 2026 AgentFlow-Eval */
/**
 * Bootstrap API key for private Docker / packaged deploys.
 *
 * Priority:
 * 1) URL query ?api_key=... (one-shot, then stripped from URL)
 * 2) Existing localStorage agentflow_settings.apiKey
 * 3) /runtime-config.json written by nginx entrypoint from API_KEYS
 */
import { readLocalApiKey, writeLocalApiKey } from "./settings-storage";

type RuntimeConfig = {
  apiKey?: string;
  authHint?: string;
};

function takeQueryApiKey(): string {
  try {
    const url = new URL(window.location.href);
    const key =
      (url.searchParams.get("api_key") || url.searchParams.get("apiKey") || "").trim();
    if (!key) return "";
    url.searchParams.delete("api_key");
    url.searchParams.delete("apiKey");
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    return key;
  } catch {
    return "";
  }
}

async function fetchRuntimeApiKey(): Promise<string> {
  try {
    const res = await fetch("/runtime-config.json", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return "";
    const data = (await res.json()) as RuntimeConfig;
    return (data.apiKey || "").trim();
  } catch {
    return "";
  }
}

/** Ensure localStorage has an API key when the stack provides one. */
export async function bootstrapApiKey(): Promise<string> {
  const fromQuery = takeQueryApiKey();
  if (fromQuery) {
    writeLocalApiKey(fromQuery);
    return fromQuery;
  }

  const existing = readLocalApiKey();
  if (existing) return existing;

  const fromRuntime = await fetchRuntimeApiKey();
  if (fromRuntime) {
    writeLocalApiKey(fromRuntime);
    return fromRuntime;
  }

  return "";
}

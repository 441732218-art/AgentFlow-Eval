/* (c) 2026 AgentFlow-Eval */
import { apiClient } from "../client";

export type MarketPlugin = {
  id: string;
  name: string;
  version: string;
  description: string;
  author?: string;
  plugin_type: string;
  tags?: string[];
  installed?: boolean;
  active?: boolean;
  is_paid?: boolean;
  price_cents?: number;
  entitled?: boolean;
  entitlement_reason?: string;
  entry?: string;
};

export type InstalledPlugin = {
  plugin_id: string;
  state: string;
  entry?: string;
  plugin_type?: string;
  meta?: Record<string, unknown> | null;
  error?: string | null;
};

export const pluginsApi = {
  market: (params?: { tag?: string; type?: string }) =>
    apiClient
      .get<{ items: MarketPlugin[]; total: number; plan_code?: string }>(
        "/plugins/market",
        { params }
      )
      .then((r) => r.data),
  marketMeta: (catalogId: string) =>
    apiClient.get(`/plugins/market/${catalogId}/meta`).then((r) => r.data),
  install: (catalog_id: string, activate = true) =>
    apiClient
      .post("/plugins/market/install", { catalog_id, activate })
      .then((r) => r.data),
  uninstall: (catalog_id: string) =>
    apiClient
      .post("/plugins/market/uninstall", { catalog_id })
      .then((r) => r.data),
  list: () =>
    apiClient
      .get<{ items: InstalledPlugin[]; total: number; status: unknown }>(
        "/plugins"
      )
      .then((r) => r.data),
  status: () => apiClient.get("/plugins/status").then((r) => r.data),
  activate: (pluginId: string) =>
    apiClient.post(`/plugins/${pluginId}/activate`).then((r) => r.data),
  deactivate: (pluginId: string) =>
    apiClient.post(`/plugins/${pluginId}/deactivate`).then((r) => r.data),
  unload: (pluginId: string) =>
    apiClient.delete(`/plugins/${pluginId}`).then((r) => r.data),
};

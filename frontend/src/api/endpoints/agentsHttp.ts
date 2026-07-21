import { apiClient } from "../client";

export interface HttpAgentProbeRequest {
  endpoint_url: string;
  timeout_sec?: number;
  headers?: Record<string, string>;
  method?: string;
  query?: string;
  verify_ssl?: boolean;
}

export interface HttpAgentProbeResponse {
  ok: boolean;
  reachable: boolean;
  protocol_compatible: boolean;
  ssrf_blocked: boolean;
  latency_ms: number | null;
  http_status: number | null;
  endpoint: string;
  protocol_version: string;
  final_answer_preview: string;
  steps_count: number;
  normalized_status: string;
  error: string | null;
  detail?: Record<string, unknown>;
}

export interface HttpAgentContract {
  protocol_version: string;
  request: Record<string, unknown>;
  response_accepted: unknown[];
  agent_config_fields: Record<string, unknown>;
  docs: string;
}

export const agentsHttpApi = {
  probe: (body: HttpAgentProbeRequest) =>
    apiClient
      .post<HttpAgentProbeResponse>("/agents/http/probe", body)
      .then((r) => r.data),

  contract: () =>
    apiClient.get<HttpAgentContract>("/agents/http/contract").then((r) => r.data),
};

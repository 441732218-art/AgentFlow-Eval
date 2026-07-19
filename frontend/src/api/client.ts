import axios from "axios";
import type { AxiosInstance } from "axios";
import { readLocalApiKey } from "@/lib/settings-storage";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const key = readLocalApiKey();
  if (key) {
    config.headers = config.headers || {};
    config.headers["X-API-Key"] = key;
  }
  return config;
});

function extractErrorMessage(error: any): string {
  const data = error?.response?.data;
  const status: number | undefined = error?.response?.status;

  // Quota exceeded (enterprise: 429 QUOTA_EXCEEDED; legacy also used 402)
  if (status === 429) {
    const code = data?.error?.detail?.code || data?.error?.code;
    const structured =
      data?.error?.message ||
      (typeof data?.error?.detail === "string" ? data.error.detail : null) ||
      data?.detail;
    if (code === "QUOTA_EXCEEDED" || /quota/i.test(String(structured || ""))) {
      return `额度超限（429 QUOTA_EXCEEDED）：${
        typeof structured === "string" ? structured : "请升级套餐或等待账期重置"
      }`;
    }
  }

  // Auth required — guide user to Settings / ApiKeyGate
  if (status === 401) {
    const structured =
      data?.error?.message ||
      data?.error?.detail ||
      (typeof data?.detail === "string" ? data.detail : null);
    if (structured && typeof structured === "string" && structured !== "Unauthorized") {
      return `${structured}（请在设置中填写 API Key，或检查 backend API_KEYS）`;
    }
    return "未授权：后端已开启 AUTH_ENABLED，请在「设置」填写 API Key（API_KEYS 的 secret 段）";
  }

  // Structured backend error: { error: { message, detail } }
  const structured =
    data?.error?.message ||
    (typeof data?.error?.detail === "string" ? data.error.detail : null);
  if (structured && typeof structured === "string") {
    if (status === 402) {
      return `额度不足：${structured}（可前往「用量计费」升级套餐或开启账期）`;
    }
    return structured;
  }

  // FastAPI / Starlette style
  if (typeof data?.detail === "string") {
    if (status === 402) return `额度不足：${data.detail}`;
    return data.detail;
  }
  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((d: any) => d?.msg || d?.message || JSON.stringify(d))
      .join("; ");
  }
  if (typeof data?.message === "string") return data.message;
  if (status === 402) return "额度不足（HTTP 402），请检查用量与套餐";

  // Vite proxy returns 500 HTML/text when backend is down
  if (status === 500 || status === 502 || status === 503 || status === 504) {
    const body = typeof data === "string" ? data : "";
    if (
      !data?.error &&
      (body.includes("ECONNREFUSED") ||
        body.includes("proxy") ||
        body.includes("Error occurred while trying to proxy") ||
        !body)
    ) {
      return "后端服务不可用（代理返回 " + status + "）。请先启动 API：http://localhost:8000";
    }
    return `服务器错误 (${status})。请检查后端日志，或确认 API 已在 8000 端口运行。`;
  }

  if (!error?.response) {
    if (error?.code === "ECONNABORTED") return "请求超时，请稍后重试";
    return "无法连接后端，请确认 API 已启动（默认 http://localhost:8000）";
  }

  return error?.message || "Request failed";
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = extractErrorMessage(error);
    console.error("[API Error]", message, error?.response?.status);
    // Reject with Error so React Query / UI show a clear message
    // instead of axios default "Request failed with status code 500"
    const enriched = new Error(message) as Error & {
      response?: unknown;
      status?: number;
      original?: unknown;
    };
    enriched.response = error?.response;
    enriched.status = error?.response?.status;
    enriched.original = error;
    return Promise.reject(enriched);
  },
);

export { apiClient };

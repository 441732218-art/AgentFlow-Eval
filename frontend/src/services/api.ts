/* (c) 2026 AgentFlow-Eval */
/* 兼容层：统一转发到 @/api/client，避免双 Axios 实例 */

export { apiClient as default, apiClient } from "@/api/client";

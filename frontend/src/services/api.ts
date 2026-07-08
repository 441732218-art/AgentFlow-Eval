/* (c) 2026 AgentFlow-Eval */
/* Axios 实例配置 */

import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.error?.message ||
      error.message ||
      "请求失败，请稍后重试";
    console.error("[API Error]", message, error);
    return Promise.reject(error);
  },
);

export default api;

import axios from "axios";
import type { AxiosInstance } from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.error?.message ||
      error.message ||
      "Request failed";
    console.error("[API Error]", message);
    return Promise.reject(error);
  },
);

export { apiClient };

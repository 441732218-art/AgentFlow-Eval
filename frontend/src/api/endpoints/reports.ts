import { apiClient } from "../client";
import type { TaskReport } from "@/types";

export const reportApi = {
  get: (taskId: string) =>
    apiClient.get<TaskReport>(`/reports/${taskId}`).then((r) => r.data),
};

import { apiClient } from "../client";
import type { Trace, JudgeResult, PaginatedResponse } from "@/types";

export const traceApi = {
  list: (params?: {
    test_suite_id?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<PaginatedResponse<Trace>>("/traces", { params }).then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Trace>(`/traces/${id}`).then((r) => r.data),

  judge: (traceId: string) =>
    apiClient.post<JudgeResult>(`/traces/${traceId}/judge`).then((r) => r.data),
};

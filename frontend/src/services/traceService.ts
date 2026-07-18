/* (c) 2026 AgentFlow-Eval
 * @deprecated Use `@/api/endpoints/traces` (`traceApi`) instead.
 */
import { traceApi } from "@/api/endpoints/traces";
import type { Trace, TraceListResponse, JudgeResult } from "../types";

/** @deprecated Prefer `traceApi` from `@/api` */
export const traceService = {
  async list(params?: {
    test_suite_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<TraceListResponse> {
    return traceApi.list(params) as Promise<TraceListResponse>;
  },

  async getById(id: string): Promise<Trace> {
    return traceApi.get(id);
  },

  async judge(id: string): Promise<JudgeResult> {
    return traceApi.judge(id);
  },
};

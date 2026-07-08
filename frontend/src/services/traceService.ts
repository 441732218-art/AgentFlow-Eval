/* (c) 2026 AgentFlow-Eval */

import api from "./api";
import type { Trace, TraceListResponse, JudgeResult } from "../types";

export const traceService = {
  /** 获取轨迹列表 */
  async list(params?: {
    test_suite_id?: string;
    page?: number;
    page_size?: number;
  }): Promise<TraceListResponse> {
    const { data } = await api.get<TraceListResponse>("/traces", { params });
    return data;
  },

  /** 获取轨迹详情 */
  async getById(id: string): Promise<Trace> {
    const { data } = await api.get<Trace>(`/traces/${id}`);
    return data;
  },

  /** 对轨迹执行 LLM 评分 */
  async judge(id: string): Promise<JudgeResult> {
    const { data } = await api.post<JudgeResult>(`/traces/${id}/judge`);
    return data;
  },
};

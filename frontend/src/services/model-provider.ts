/**
 * model-provider.ts
 * Judge Scorecard API 封装
 *
 * ⚠️ V1.0 重构说明：
 * 旧版在前端直连 LLM 执行 Judge，现已迁移至后端 Celery task (run_judge_evaluation)。
 * 本文件仅保留 Scorecard 配置/校验接口，以及对旧 API 的废弃兼容层。
 */

import { apiClient } from "@/api/client";

// ======================== Scorecard 类型 ========================

export interface ScorecardDimension {
  key: string;
  label: string;
  weight: number;
  description?: string;
}

export interface Scorecard {
  dimensions: ScorecardDimension[];
  version?: string;
}

export interface DefaultScorecardResponse {
  scorecard: Scorecard;
  weight_sum: number;
  notes: string;
}

export interface ValidateScorecardResponse {
  ok: boolean;
  scorecard: Scorecard;
  weight_sum: number;
}

// ======================== Scorecard API ========================

/** 获取默认评分卡 (40/40/20) */
export async function getDefaultScorecard(): Promise<DefaultScorecardResponse> {
  const res = await apiClient.get("/judges/scorecards/default");
  return res.data;
}

/** 校验自定义评分卡（唯一 key、正权重、归一化到 100） */
export async function validateScorecard(
  scorecard: Record<string, unknown>,
): Promise<ValidateScorecardResponse> {
  const res = await apiClient.post("/judges/scorecards/validate", { scorecard });
  return res.data;
}

// ======================== 废弃兼容层 ========================

/**
 * @deprecated V1.0 起 Judge 执行已迁移至后端 Celery task。
 * 请使用 taskApi.create() 创建评测任务，后端自动触发 Judge。
 */
export type ProviderType = "openai" | "anthropic" | "azure" | "zhipu" | "local";

/** @deprecated 同上 */
export interface ModelProviderConfig {
  id: string;
  name: string;
  type: ProviderType;
  baseUrl: string;
  apiKey: string;
  modelName: string;
}

/** @deprecated 同上 */
export interface JudgeRequest {
  providerId: string;
  messages: { role: "system" | "user" | "assistant"; content: string }[];
  responseFormat?: "json" | "text";
}

/** @deprecated 同上 */
export interface JudgeResponse {
  success: boolean;
  content: string;
  parsed?: Record<string, unknown>;
  latencyMs: number;
  error?: string;
}

const DEPRECATED_MSG =
  "[model-provider] judge() 已在 V1.0 移除。请通过 taskApi.create() 创建评测任务，由后端 Celery 执行 Judge。";

/** @deprecated 使用 taskApi.create() 代替 */
export const modelProviderService = {
  judge: async (_req: JudgeRequest): Promise<JudgeResponse> => {
    console.error(DEPRECATED_MSG);
    throw new Error(DEPRECATED_MSG);
  },
  judgeWithRetry: async (_req: JudgeRequest): Promise<JudgeResponse> => {
    console.error(DEPRECATED_MSG);
    throw new Error(DEPRECATED_MSG);
  },
  checkHealth: async () => ({
    providerId: "",
    available: false,
    latencyMs: 0,
    message: DEPRECATED_MSG,
  }),
  registerProvider: () => console.warn(DEPRECATED_MSG),
  getProviders: () => [] as ModelProviderConfig[],
};

export default modelProviderService;

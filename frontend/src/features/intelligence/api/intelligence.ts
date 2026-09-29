import { apiClient } from "@/api/client";
import type {
  AgentIntelligenceConsole,
  InsightDetail,
  InsightExplanation,
  QualityAssessmentExplanation,
  RecommendationListResponse,
} from "../types/console";

export const intelligenceApi = {
  getConsole: (agentId: string, params?: { include_trend?: boolean; agent_version?: string }) =>
    apiClient
      .get<AgentIntelligenceConsole>(`/intelligence/agents/${encodeURIComponent(agentId)}/console`, {
        params: {
          include_trend: params?.include_trend ?? true,
          agent_version: params?.agent_version,
        },
      })
      .then((r) => r.data),

  getInsight: (insightId: string) =>
    apiClient
      .get<InsightDetail>(`/intelligence/insights/${encodeURIComponent(insightId)}`)
      .then((r) => r.data),

  getInsightExplanation: (insightId: string) =>
    apiClient
      .get<InsightExplanation>(
        `/intelligence/insights/${encodeURIComponent(insightId)}/explanation`,
      )
      .then((r) => r.data),

  acknowledgeInsight: (insightId: string) =>
    apiClient
      .post(`/intelligence/insights/${encodeURIComponent(insightId)}/acknowledge`)
      .then((r) => r.data),

  resolveInsight: (insightId: string) =>
    apiClient
      .post(`/intelligence/insights/${encodeURIComponent(insightId)}/resolve`)
      .then((r) => r.data),

  listRecommendations: (agentId: string, agentVersion?: string) =>
    apiClient
      .get<RecommendationListResponse>(
        `/intelligence/agents/${encodeURIComponent(agentId)}/recommendations`,
        { params: { agent_version: agentVersion } },
      )
      .then((r) => r.data),

  getQualityAssessmentExplanation: (assessmentId: string) =>
    apiClient
      .get<QualityAssessmentExplanation>(
        `/intelligence/quality-assessments/${encodeURIComponent(assessmentId)}/explanation`,
      )
      .then((r) => r.data),
};

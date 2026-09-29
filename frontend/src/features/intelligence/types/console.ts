/** Agent Intelligence Console — frontend contracts (mirror backend projection). */

export type QualityPosture = "healthy" | "degraded" | "risk_detected" | "unknown";

export type InsightSummaryRow = {
  insight_id: string;
  severity: string;
  status: string;
};

export type RecommendationSummaryRow = {
  recommendation_id: string;
  type: string;
  group: string;
  priority: string;
};

export type QualityTrendPoint = {
  timestamp: string;
  posture: QualityPosture | string;
  score_delta: number | null;
  insight_count: number;
  regression_detected: boolean;
  agent_version?: string | null;
  evaluation_id?: string | null;
};

export type AgentIntelligenceConsole = {
  agent_id: string;
  quality_posture: QualityPosture | string;
  quality_explanation_ref: string | null;
  top_insights: InsightSummaryRow[];
  top_recommendations: RecommendationSummaryRow[];
  trend_points: QualityTrendPoint[];
  open_insight_count: number;
  generated_at: string | null;
};

export type InsightDetail = {
  insight_id: string;
  agent_id?: string;
  agent_version?: string | null;
  insight_type?: string;
  severity?: string;
  summary?: string;
  status?: string;
  evidence_refs?: Array<{ type: string; id: string }>;
  [key: string]: unknown;
};

export type InsightExplanation = {
  insight_id?: string;
  summary?: string;
  reason?: string;
  evidence_refs?: Array<{ type: string; id: string }>;
  context_refs?: Array<{ type: string; id: string }>;
  snapshot_refs?: Array<{ snapshot_id: string; snapshot_type: string }>;
  [key: string]: unknown;
};

export type RecommendationListItem = {
  recommendation_id: string;
  agent_id?: string | null;
  agent_version?: string | null;
  recommendation_type?: string;
  recommendation_group?: string;
  priority?: string;
  explanation?: {
    reason?: string;
    evidence_refs?: Array<{ type: string; id: string }>;
    related_insight_ids?: string[];
  } | null;
  evidence_refs?: Array<{ type: string; id: string }>;
  related_insight_ids?: string[];
  created_at?: string | null;
};

export type RecommendationListResponse = {
  recommendations: RecommendationListItem[];
  count: number;
};

export type QualityAssessmentExplanation = {
  assessment_id: string;
  posture: string;
  summary: string;
  insight_refs: Array<{ type: string; id: string }>;
  recommendation_refs: Array<{ type: string; id: string }>;
  snapshot_refs: Array<{ snapshot_id: string; snapshot_type: string }>;
  created_at: string | null;
};

export function normalizePosture(value: string | null | undefined): QualityPosture {
  const normalized = (value || "").trim().toLowerCase();
  if (
    normalized === "healthy" ||
    normalized === "degraded" ||
    normalized === "risk_detected" ||
    normalized === "unknown"
  ) {
    return normalized;
  }
  return "unknown";
}

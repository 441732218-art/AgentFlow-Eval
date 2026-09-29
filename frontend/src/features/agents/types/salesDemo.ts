export interface SalesDemoCase {
  case_id: string;
  customer_id: string;
  customer_inquiry: string;
  expected_product: string;
  expected_tone: string;
  expected_action: string;
}

export interface SalesToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  output: unknown;
}

export interface SalesEvaluationScore {
  response_quality: number;
  product_accuracy: number;
  customer_match: number;
  business_compliance: number;
  total: number;
}

export interface SalesDemoResult {
  execution_id: string;
  case_id: string;
  customer: Record<string, unknown> | null;
  inquiry: string;
  tool_calls: SalesToolCall[];
  product_matches: Record<string, unknown>[];
  email_draft: { subject: string; body: string; tone?: string } | null;
  crm_activity: Record<string, unknown> | null;
  evaluation_score: SalesEvaluationScore;
  status: string;
}

export interface SalesDemoRunResponse {
  demo: SalesDemoResult;
  trace: Record<string, unknown>[];
  evidence: Record<string, unknown> | null;
}

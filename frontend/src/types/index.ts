/* (c) 2026 AgentFlow-Eval */
/* AgentFlow-Eval Frontend TypeScript Types */

export type TaskStatus =
  | "created"
  | "queued"
  | "running"
  | "waiting_tool"
  | "judging"
  | "completed"
  | "failed"
  | "cancelled"
  | "timeout"
  | "partial";

export type TraceStatus = "success" | "failed";

export interface Task {
  id: string;
  name: string;
  description: string;
  status: TaskStatus;
  agent_config: Record<string, unknown>;
  celery_task_id: string | null;
  is_archived?: boolean;
  created_by?: string;
  created_at: string | null;
  updated_at: string | null;
  test_suite_count: number;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskCreatePayload {
  name: string;
  description?: string;
  agent_config?: Record<string, unknown>;
}

export interface MetricScore {
  id: string;
  metric_name: string;
  score: number;
  reason: string;
  extra_metadata: Record<string, unknown> | null;
}

export interface TraceStep {
  iteration?: number;
  role: string;
  type?: string;
  content?: string;
  tool_name?: string;
  tool_input?: string;
  thought?: string;
  action?: string;
  action_input?: string;
  observation?: string;
  tokens?: number;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

export interface Trace {
  id: string;
  test_suite_id: string;
  user_query: string;
  steps: TraceStep[];
  total_tokens: number;
  response_time_ms: number;
  status: TraceStatus;
  created_at: string | null;
  metric_scores: MetricScore[];
  /** Observability metadata (optional on legacy rows) */
  prompt_tokens?: number;
  completion_tokens?: number;
  cost?: number;
  agent_version?: string | null;
  prompt_version?: string | null;
  model_version?: string | null;
  tool_version?: string | null;
  token_usage?: TokenUsage | null;
}

export interface TraceListResponse {
  items: Trace[];
  total: number;
}

export interface JudgeResult {
  scores: Record<string, number>;
  total: number;
  reason: string;
  token_cost: number;
}

export interface TaskReport {
  task: {
    id: string;
    name: string;
    description: string;
    status: TaskStatus;
    created_at: string | null;
  };
  summary: {
    total_suites: number;
    total_traces: number;
    success_count: number;
    failed_count: number;
    total_tokens: number;
    total_time_ms: number;
    avg_time_per_trace_ms: number;
    overall_score: number;
    dimension_scores: Record<string, number>;
  };
  details: Array<{
    suite_id: string;
    user_query: string;
    expected_output: string;
    expected_tools: string[];
    traces: Array<{
      trace_id: string;
      status: string;
      total_tokens: number;
      response_time_ms: number;
      scores: Record<string, number>;
      created_at: string | null;
    }>;
  }>;
}

// ---- API layer types ----

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface TaskCreate {
  name: string;
  description?: string;
  agent_config?: Record<string, unknown>;
}

export interface CreateTestSuiteInput {
  user_query: string;
  expected_output?: string;
  expected_tools?: string[];
}

export interface ExecuteTaskResponse {
  task_id: string;
  status: string;
  celery_task_id: string;
  message: string;
}

export interface CreateTestSuitesResponse {
  task_id: string;
  created: number;
}

// ---- TanStack Query params ----

export interface TaskListParams {
  page?: number;
  page_size?: number;
  status?: string;
  include_archived?: boolean;
}

export interface TraceListParams {
  test_suite_id?: string;
  page?: number;
  page_size?: number;
}

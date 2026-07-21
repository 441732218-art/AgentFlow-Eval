import { apiClient } from "../client";

export interface ScoreDimension {
  key: string;
  label?: string;
  weight: number;
  description?: string;
  method?: "rule_tool" | "lexical" | "llm_only" | "llm_or_lexical";
}

export interface Scorecard {
  version?: number;
  name?: string;
  dimensions: ScoreDimension[];
  llm_refine?: boolean;
  normalize_weights?: boolean;
}

export const judgesApi = {
  defaultScorecard: () =>
    apiClient
      .get<{ scorecard: Scorecard; weight_sum: number }>("/judges/scorecards/default")
      .then((r) => r.data),

  validateScorecard: (scorecard: Scorecard) =>
    apiClient
      .post<{ ok: boolean; scorecard: Scorecard; weight_sum: number }>(
        "/judges/scorecards/validate",
        { scorecard }
      )
      .then((r) => r.data),
};

/** Built-in default matching backend (offline fallback). */
export const DEFAULT_SCORECARD: Scorecard = {
  version: 1,
  name: "default_agent_eval",
  llm_refine: true,
  dimensions: [
    {
      key: "tool_accuracy",
      label: "工具调用准确率",
      weight: 40,
      description: "是否按预期调用工具",
      method: "rule_tool",
    },
    {
      key: "answer_correctness",
      label: "答案准确性",
      weight: 40,
      description: "与 expected_output 一致性",
      method: "llm_or_lexical",
    },
    {
      key: "reasoning_coherence",
      label: "推理连贯性",
      weight: 20,
      description: "步骤是否自洽",
      method: "llm_only",
    },
  ],
};

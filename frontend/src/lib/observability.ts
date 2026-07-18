/** Shared labels / helpers for Trace · Diagnosis · Analytics */

import type { TraceStep } from "@/types";

export const ISSUE_LABEL: Record<string, string> = {
  agent_loop: "Agent Loop",
  tool_failure: "Tool Failure",
  token_drift: "Token Drift",
  prompt_drift: "Prompt Drift",
  timeout: "Timeout",
  healthy: "Healthy",
};

export const ISSUE_COLOR: Record<string, string> = {
  agent_loop: "purple",
  tool_failure: "error",
  token_drift: "warning",
  prompt_drift: "processing",
  timeout: "orange",
  healthy: "success",
};

export const ISSUE_TONE: Record<
  string,
  "cyan" | "success" | "warning" | "danger" | "purple"
> = {
  agent_loop: "purple",
  tool_failure: "danger",
  token_drift: "warning",
  prompt_drift: "cyan",
  timeout: "warning",
  healthy: "success",
};

export function stepLabel(step: TraceStep, idx: number): string {
  const t = step.type || step.role || "step";
  if (step.tool_name) return `${t}: ${step.tool_name}`;
  if (step.action) return `${t}: ${step.action}`;
  return `${t} #${idx + 1}`;
}

export function stepBody(step: TraceStep): string {
  return (
    step.content ||
    step.thought ||
    step.observation ||
    step.tool_input ||
    step.action_input ||
    JSON.stringify(step, null, 2)
  );
}

export function stepKind(step: TraceStep): string {
  const t = (step.type || step.role || "").toLowerCase();
  if (t.includes("thought") || t === "assistant") return "thought";
  if (t.includes("action") || t.includes("tool") || step.tool_name) return "action";
  if (t.includes("obs") || t.includes("tool_result")) return "observation";
  if (t.includes("final") || t.includes("answer")) return "final_answer";
  return t || "step";
}

/** Map free-form metric names → radar dimensions */
export function mapMetricToDimension(name: string): string | null {
  const n = name.toLowerCase();
  if (/reason|think|plan|logic/.test(n)) return "Reasoning";
  if (/accura|correct|match|answer|quality|score|overall/.test(n)) return "Accuracy";
  if (/tool|function|api|action/.test(n)) return "Tool Usage";
  if (/speed|latenc|time|efficien/.test(n)) return "Speed";
  if (/cost|token|price|budget/.test(n)) return "Cost";
  if (/safe|harm|policy|refus/.test(n)) return "Safety";
  return null;
}

export function shortId(id: string, n = 8): string {
  if (!id) return "—";
  return id.length <= n ? id : `${id.slice(0, n)}…`;
}

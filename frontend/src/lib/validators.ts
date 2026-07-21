import { z } from "zod";

export const taskCreateSchema = z
  .object({
    name: z
      .string()
      .trim()
      .min(1, "任务名称是必需的")
      .max(255, "任务名称最多 255 个字符"),
    description: z.string().optional().default(""),
    runner: z.enum(["openai", "http"]).optional().default("openai"),
    model: z.string().optional().default("gpt-4o"),
    temperature: z.number().min(0).max(2).optional().default(0),
    max_tokens: z.number().min(256).max(16384).optional().default(4096),
    // HTTP agent fields
    endpoint_url: z.string().optional().default(""),
    timeout_sec: z.number().min(1).max(300).optional().default(60),
    headers_json: z.string().optional().default(""),
    verify_ssl: z.boolean().optional().default(true),
  })
  .superRefine((data, ctx) => {
    if (data.runner === "http") {
      const url = (data.endpoint_url || "").trim();
      if (!url) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "HTTP Runner 需要填写 endpoint_url",
          path: ["endpoint_url"],
        });
      } else if (!/^https?:\/\//i.test(url)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "endpoint_url 必须以 http:// 或 https:// 开头",
          path: ["endpoint_url"],
        });
      }
      if (data.headers_json?.trim()) {
        try {
          const parsed = JSON.parse(data.headers_json);
          if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
            throw new Error("not object");
          }
        } catch {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Headers 必须是合法 JSON 对象，例如 {\"Authorization\":\"Bearer x\"}",
            path: ["headers_json"],
          });
        }
      }
    }
  });

export type TaskCreateInput = z.infer<typeof taskCreateSchema>;

/** Build backend agent_config from create-task form values. */
export function buildAgentConfigFromForm(data: TaskCreateInput): Record<string, unknown> {
  const runner = data.runner || "openai";
  if (runner === "http") {
    let headers: Record<string, string> = {};
    if (data.headers_json?.trim()) {
      try {
        headers = JSON.parse(data.headers_json) as Record<string, string>;
      } catch {
        headers = {};
      }
    }
    return {
      runner: "http",
      endpoint_url: (data.endpoint_url || "").trim(),
      timeout_sec: data.timeout_sec ?? 60,
      headers,
      method: "POST",
      verify_ssl: data.verify_ssl ?? true,
    };
  }
  return {
    runner: "openai",
    model: data.model || "gpt-4o",
    temperature: data.temperature ?? 0,
    max_tokens: data.max_tokens ?? 4096,
  };
}

export const testSuiteSchema = z.object({
  query: z.string().min(1, "Query is required"),
  expected_output: z.string().optional().default(""),
  expected_tools: z.string().optional().default(""),
});

export const csvRowSchema = z.object({
  query: z.string().min(1),
  expected_output: z.string().optional().default(""),
  expected_tools: z.string().optional().default(""),
});

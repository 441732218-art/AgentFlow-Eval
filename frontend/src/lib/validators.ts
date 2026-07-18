import { z } from "zod";

export const taskCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "任务名称是必需的")
    .max(255, "任务名称最多 255 个字符"),
  description: z.string().optional().default(""),
  model: z.string().optional().default("gpt-4o"),
  temperature: z.number().min(0).max(2).optional().default(0),
  max_tokens: z.number().min(256).max(16384).optional().default(4096),
});

export type TaskCreateInput = z.infer<typeof taskCreateSchema>;

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

/* (c) 2026 AgentFlow-Eval */
import { apiClient } from "../client";

export type BillingPlan = {
  id: string;
  code: string;
  name: string;
  description: string;
  price_month_cents: number;
  token_quota: number;
  task_quota: number;
  features: Record<string, unknown>;
  is_public: boolean;
};

export type QuotaResponse = {
  actor: string;
  period: string;
  token_used: number;
  token_limit: number;
  task_used: number;
  task_limit: number;
  plan_code: string;
  subscription_status: string;
  billing_enabled: boolean;
};

export type UsageItem = {
  id: string;
  metric: string;
  quantity: number;
  ref_type?: string | null;
  ref_id?: string | null;
  trace_id?: string | null;
  created_at?: string | null;
};

export type InvoiceItem = {
  id: string;
  period: string;
  amount_cents: number;
  status: string;
  line_items: unknown[];
  issued_at?: string | null;
};

export const billingApi = {
  plans: () =>
    apiClient
      .get<{ items: BillingPlan[]; total: number; billing_enabled: boolean }>(
        "/billing/plans"
      )
      .then((r) => r.data),
  quota: () => apiClient.get<QuotaResponse>("/billing/quota").then((r) => r.data),
  usage: (limit = 50) =>
    apiClient
      .get<{ items: UsageItem[]; total: number }>("/billing/usage", {
        params: { limit },
      })
      .then((r) => r.data),
  invoices: () =>
    apiClient
      .get<{ items: InvoiceItem[]; total: number }>("/billing/invoices")
      .then((r) => r.data),
  subscribe: (plan_code: string) =>
    apiClient.post("/billing/subscribe", { plan_code }).then((r) => r.data),
  checkout: (plan_code: string) =>
    apiClient
      .post<{
        checkout?: {
          session_id: string;
          url: string;
          mode: string;
          plan_code: string;
          amount_cents?: number;
        };
        mode?: string;
        subscription?: unknown;
        stripe_mode?: string;
      }>("/billing/checkout", { plan_code })
      .then((r) => r.data),
  mockConfirm: (body: {
    session_id: string;
    plan_code: string;
    actor?: string;
  }) =>
    apiClient.post("/billing/checkout/mock-confirm", body).then((r) => r.data),
  draftInvoice: () =>
    apiClient.post("/billing/invoices/draft").then((r) => r.data),
};

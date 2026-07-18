/* (c) 2026 AgentFlow-Eval */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { billingApi } from "@/api/endpoints/billing";

export const BILLING_PLANS_KEY = ["billing", "plans"] as const;
export const BILLING_QUOTA_KEY = ["billing", "quota"] as const;
export const BILLING_USAGE_KEY = ["billing", "usage"] as const;
export const BILLING_INVOICES_KEY = ["billing", "invoices"] as const;

export function useBillingPlans() {
  return useQuery({
    queryKey: BILLING_PLANS_KEY,
    queryFn: () => billingApi.plans(),
    staleTime: 120_000,
  });
}

export function useBillingQuota() {
  return useQuery({
    queryKey: BILLING_QUOTA_KEY,
    queryFn: () => billingApi.quota(),
    staleTime: 30_000,
  });
}

export function useBillingUsage(limit = 50) {
  return useQuery({
    queryKey: [...BILLING_USAGE_KEY, limit],
    queryFn: () => billingApi.usage(limit),
    staleTime: 30_000,
  });
}

export function useBillingInvoices() {
  return useQuery({
    queryKey: BILLING_INVOICES_KEY,
    queryFn: () => billingApi.invoices(),
    staleTime: 60_000,
  });
}

export function useSubscribePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (plan_code: string) => billingApi.subscribe(plan_code),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILLING_QUOTA_KEY });
      void qc.invalidateQueries({ queryKey: BILLING_PLANS_KEY });
    },
  });
}

/** Paid plans: create Checkout (mock/live). Free plans return direct subscribe. */
export function useCheckoutPlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (plan_code: string) => {
      const data = await billingApi.checkout(plan_code);
      // Mock mode: auto-confirm so demo works without real Stripe
      if (data.checkout?.mode === "mock" && data.checkout.session_id) {
        await billingApi.mockConfirm({
          session_id: data.checkout.session_id,
          plan_code: data.checkout.plan_code || plan_code,
        });
        return { ...data, mock_confirmed: true };
      }
      // Live: caller should redirect to data.checkout.url
      return { ...data, mock_confirmed: false };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILLING_QUOTA_KEY });
      void qc.invalidateQueries({ queryKey: BILLING_PLANS_KEY });
      void qc.invalidateQueries({ queryKey: BILLING_INVOICES_KEY });
    },
  });
}

export function useDraftInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => billingApi.draftInvoice(),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILLING_INVOICES_KEY });
    },
  });
}

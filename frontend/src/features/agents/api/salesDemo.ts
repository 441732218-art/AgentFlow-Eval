import { apiClient } from "@/api/client";
import type { SalesDemoCase, SalesDemoRunResponse } from "../types/salesDemo";

export const salesDemoApi = {
  listCases: () =>
    apiClient
      .get<{ cases: SalesDemoCase[]; count: number }>("/business/sales/cases")
      .then((r) => r.data),

  runDemo: (payload: { case_id?: string; inquiry?: string; customer_id?: string }) =>
    apiClient
      .post<SalesDemoRunResponse>("/business/sales/demo/run", payload)
      .then((r) => r.data),
};

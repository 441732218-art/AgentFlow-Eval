/* (c) 2026 AgentFlow-Eval */

import { create } from "zustand";
import type { Trace, JudgeResult } from "../types";
import { traceApi } from "@/api/endpoints/traces";

interface TraceState {
  traces: Trace[];
  total: number;
  loading: boolean;
  currentTrace: Trace | null;
  currentJudgeResult: JudgeResult | null;

  fetchTraces: (testSuiteId?: string) => Promise<void>;
  fetchTrace: (id: string) => Promise<void>;
  judgeTrace: (id: string) => Promise<void>;
  reset: () => void;
}

export const useTraceStore = create<TraceState>((set) => ({
  traces: [],
  total: 0,
  loading: false,
  currentTrace: null,
  currentJudgeResult: null,

  fetchTraces: async (testSuiteId?: string) => {
    set({ loading: true });
    try {
      const res = await traceApi.list({ test_suite_id: testSuiteId, page_size: 50 });
      set({ traces: res.items, total: res.total });
    } finally {
      set({ loading: false });
    }
  },

  fetchTrace: async (id: string) => {
    set({ loading: true });
    try {
      const trace = await traceApi.get(id);
      set({ currentTrace: trace });
    } finally {
      set({ loading: false });
    }
  },

  judgeTrace: async (id: string) => {
    set({ loading: true });
    try {
      const result = await traceApi.judge(id);
      set({ currentJudgeResult: result });
    } finally {
      set({ loading: false });
    }
  },

  reset: () => set({ traces: [], total: 0, loading: false, currentTrace: null, currentJudgeResult: null }),
}));

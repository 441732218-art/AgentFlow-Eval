/* (c) 2026 AgentFlow-Eval */

import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { queryClient } from "@/lib/query-client";
import { router } from "@/router";
import { ToastProvider } from "@/components/ui/Toast";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import { AuthProvider } from "@/auth";
import { BootSplash } from "@/components/brand/BootSplash";

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BootSplash />
          <RouterProvider router={router} />
          <ToastProvider />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;

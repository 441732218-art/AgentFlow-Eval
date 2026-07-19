import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { PageSkeleton } from "@/components/ui/PageSkeleton";
import { RouteGuard } from "@/auth";
import type { Permission } from "@/auth/permissions";

const DashboardPage = lazy(() => import("@/dashboard/DashboardPage"));
const TraceExplorerPage = lazy(() => import("@/traces/TraceExplorerPage"));
const DiagnosisPage = lazy(() => import("@/diagnosis/DiagnosisPage"));
const AnalyticsPage = lazy(() => import("@/analytics/AnalyticsPage"));
const MonitoringPage = lazy(() => import("@/monitoring/MonitoringPage"));
const TaskListPage = lazy(() => import("@/pages/tasks/index"));
const CreateTaskPage = lazy(() => import("@/pages/tasks/create"));
const TaskDetailPage = lazy(() => import("@/pages/tasks/detail"));
const ReportsPage = lazy(() => import("@/pages/reports/index"));
const ReportDetailPage = lazy(() => import("@/pages/reports/ReportDetail"));
const SettingsPage = lazy(() => import("@/pages/Settings"));
const BillingPage = lazy(() => import("@/pages/billing/index"));
const BenchmarksPage = lazy(() => import("@/pages/benchmarks/index"));
const PluginsPage = lazy(() => import("@/pages/plugins/index"));
const NotFoundPage = lazy(() => import("@/pages/NotFound"));

type SkeletonVariant = "dashboard" | "cards" | "detail" | "report" | "form";

const withSuspense = (
  Component: React.LazyExoticComponent<React.ComponentType>,
  variant: SkeletonVariant = "cards",
  permission?: Permission
) => {
  const page = (
    <Suspense fallback={<PageSkeleton variant={variant} />}>
      <Component />
    </Suspense>
  );
  return permission ? <RouteGuard permission={permission}>{page}</RouteGuard> : page;
};

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: "dashboard",
        element: withSuspense(DashboardPage, "dashboard", "task:read"),
      },
      {
        path: "traces",
        element: withSuspense(TraceExplorerPage, "detail", "evaluation:read"),
      },
      {
        path: "diagnosis",
        element: withSuspense(DiagnosisPage, "detail", "evaluation:read"),
      },
      {
        path: "analytics",
        element: withSuspense(AnalyticsPage, "dashboard", "evaluation:read"),
      },
      {
        path: "monitoring",
        element: withSuspense(MonitoringPage, "dashboard", "task:read"),
      },
      // Legacy evaluation workflow
      { path: "tasks", element: withSuspense(TaskListPage, "cards", "task:read") },
      {
        path: "tasks/create",
        element: withSuspense(CreateTaskPage, "form", "task:create"),
      },
      { path: "tasks/:id", element: withSuspense(TaskDetailPage, "detail", "task:read") },
      {
        path: "reports",
        element: withSuspense(ReportsPage, "cards", "evaluation:read"),
      },
      {
        path: "reports/:id",
        element: withSuspense(ReportDetailPage, "report", "evaluation:read"),
      },
      {
        path: "evaluation",
        element: <Navigate to="/reports" replace />,
      },
      {
        path: "billing",
        element: withSuspense(BillingPage, "cards", "task:read"),
      },
      {
        path: "benchmarks",
        element: withSuspense(BenchmarksPage, "cards", "benchmark:read"),
      },
      {
        path: "plugins",
        element: withSuspense(PluginsPage, "cards", "system:config"),
      },
      {
        path: "settings",
        element: withSuspense(SettingsPage, "form", "system:config"),
      },
      { path: "404", element: withSuspense(NotFoundPage, "detail") },
      { path: "*", element: <Navigate to="/404" replace /> },
    ],
  },
]);

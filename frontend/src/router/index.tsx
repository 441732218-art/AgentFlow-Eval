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
const ExperimentListPage = lazy(() => import("@/pages/experiments/index"));
const ExperimentCreatePage = lazy(() => import("@/pages/experiments/create"));
const ExperimentDetailPage = lazy(() => import("@/pages/experiments/detail"));
const PluginsPage = lazy(() => import("@/pages/plugins/index"));
const QualityGateDashboardPage = lazy(() => import("@/pages/governance/QualityGateDashboard"));
const GovernanceEvaluationDetailPage = lazy(
  () => import("@/pages/governance/EvaluationDetail"),
);
const GovernanceBenchmarkDetailPage = lazy(() => import("@/pages/governance/BenchmarkDetail"));
const GovernanceReleaseDetailPage = lazy(
  () => import("@/pages/governance/ReleaseAssessmentDetail"),
);
const DeploymentPoliciesPage = lazy(() => import("@/pages/governance/DeploymentPolicies"));
const AgentListPage = lazy(() => import("@/features/agents/pages/AgentList"));
const AgentDetailLayout = lazy(() => import("@/features/agents/pages/AgentDetail"));
const AgentVersionsPage = lazy(() => import("@/features/agents/pages/AgentVersions"));
const AgentDeploymentsPage = lazy(() => import("@/features/agents/pages/AgentDeployments"));
const AgentExecutionsPage = lazy(() => import("@/features/agents/pages/AgentExecutions"));
const AgentTracePage = lazy(() => import("@/features/agents/pages/AgentTrace"));
const AgentEvaluationsPage = lazy(() => import("@/features/agents/pages/AgentEvaluations"));
const AgentGovernancePage = lazy(() => import("@/features/agents/pages/AgentGovernance"));
const AgentIntelligenceConsolePage = lazy(
  () => import("@/features/intelligence/pages/AgentConsolePage"),
);
const ExecutionDetailPage = lazy(() => import("@/pages/executions/ExecutionDetail"));
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
        path: "experiments",
        element: withSuspense(ExperimentListPage, "cards", "task:read"),
      },
      {
        path: "experiments/create",
        element: withSuspense(ExperimentCreatePage, "form", "task:create"),
      },
      {
        path: "experiments/:id",
        element: withSuspense(ExperimentDetailPage, "detail", "evaluation:read"),
      },
      {
        path: "governance/quality-gates",
        element: withSuspense(QualityGateDashboardPage, "cards", "task:read"),
      },
      {
        path: "governance/evaluations/:id",
        element: withSuspense(GovernanceEvaluationDetailPage, "detail", "task:read"),
      },
      {
        path: "governance/benchmarks/:id",
        element: withSuspense(GovernanceBenchmarkDetailPage, "detail", "task:read"),
      },
      {
        path: "governance/releases/:id",
        element: withSuspense(GovernanceReleaseDetailPage, "detail", "task:read"),
      },
      {
        path: "governance/policies",
        element: withSuspense(DeploymentPoliciesPage, "cards", "task:read"),
      },
      {
        path: "agents",
        element: withSuspense(AgentListPage, "cards", "task:read"),
      },
      {
        path: "intelligence",
        element: <Navigate to="/agents" replace />,
      },
      {
        path: "intelligence/agents/:agentId/console",
        element: withSuspense(
          AgentIntelligenceConsolePage,
          "detail",
          "intelligence:read",
        ),
      },
      {
        path: "agents/:id",
        element: withSuspense(AgentDetailLayout, "detail", "task:read"),
        children: [
          { path: "versions", element: withSuspense(AgentVersionsPage, "detail", "task:read") },
          {
            path: "deployments",
            element: withSuspense(AgentDeploymentsPage, "detail", "task:read"),
          },
          {
            path: "executions",
            element: withSuspense(AgentExecutionsPage, "detail", "task:read"),
          },
          { path: "trace", element: withSuspense(AgentTracePage, "detail", "task:read") },
          {
            path: "evaluations",
            element: withSuspense(AgentEvaluationsPage, "detail", "task:read"),
          },
          {
            path: "governance",
            element: withSuspense(AgentGovernancePage, "detail", "task:read"),
          },
        ],
      },
      {
        path: "executions/:id",
        element: withSuspense(ExecutionDetailPage, "detail", "task:read"),
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

import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { PageSkeleton } from "@/components/ui/PageSkeleton";

const DashboardPage = lazy(() => import("@/pages/Dashboard"));
const TaskListPage = lazy(() => import("@/pages/tasks/index"));
const CreateTaskPage = lazy(() => import("@/pages/tasks/create"));
const TaskDetailPage = lazy(() => import("@/pages/tasks/detail"));
const ReportsPage = lazy(() => import("@/pages/reports/index"));
const ReportDetailPage = lazy(() => import("@/pages/reports/ReportDetail"));
const SettingsPage = lazy(() => import("@/pages/Settings"));
const NotFoundPage = lazy(() => import("@/pages/NotFound"));

type SkeletonVariant = "dashboard" | "cards" | "detail" | "report" | "form";

const withSuspense = (
  Component: React.LazyExoticComponent<React.ComponentType>,
  variant: SkeletonVariant = "cards"
) => (
  <Suspense fallback={<PageSkeleton variant={variant} />}>
    <Component />
  </Suspense>
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: withSuspense(DashboardPage, "dashboard") },
      { path: "tasks", element: withSuspense(TaskListPage, "cards") },
      { path: "tasks/create", element: withSuspense(CreateTaskPage, "form") },
      { path: "tasks/:id", element: withSuspense(TaskDetailPage, "detail") },
      { path: "reports", element: withSuspense(ReportsPage, "cards") },
      { path: "reports/:id", element: withSuspense(ReportDetailPage, "report") },
      { path: "settings", element: withSuspense(SettingsPage, "form") },
      { path: "404", element: withSuspense(NotFoundPage, "detail") },
      { path: "*", element: <Navigate to="/404" replace /> },
    ],
  },
]);

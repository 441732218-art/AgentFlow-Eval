import { createBrowserRouter, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";

const TaskListPage = lazy(() => import("@/pages/tasks/TaskList"));
const CreateTaskPage = lazy(() => import("@/pages/tasks/CreateTask"));
const TaskDetailPage = lazy(() => import("@/pages/tasks/TaskDetail"));
const ReportDetailPage = lazy(() => import("@/pages/reports/ReportDetail"));
const SettingsPage = lazy(() => import("@/pages/Settings"));
const NotFoundPage = lazy(() => import("@/pages/NotFound"));

const withSuspense = (Component: React.LazyExoticComponent<React.ComponentType>) => (
  <Suspense fallback={<LoadingSpinner fullScreen />}>
    <Component />
  </Suspense>
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <Navigate to="/tasks" replace /> },
      { path: "tasks", element: withSuspense(TaskListPage) },
      { path: "tasks/create", element: withSuspense(CreateTaskPage) },
      { path: "tasks/:id", element: withSuspense(TaskDetailPage) },
      { path: "reports/:id", element: withSuspense(ReportDetailPage) },
      { path: "settings", element: withSuspense(SettingsPage) },
      { path: "404", element: withSuspense(NotFoundPage) },
      { path: "*", element: <Navigate to="/404" replace /> },
    ],
  },
]);

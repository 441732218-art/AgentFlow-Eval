import { Breadcrumb } from "antd";
import { Link, useLocation, useParams } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";

function buildCrumbs(pathname: string, params: Record<string, string | undefined>) {
  const items: Array<{ title: React.ReactNode }> = [
    {
      title: (
        <Link to="/dashboard">
          <HomeOutlined /> Command
        </Link>
      ),
    },
  ];

  if (pathname.startsWith("/dashboard")) {
    return items;
  } else if (pathname.startsWith("/traces")) {
    items.push({ title: "Trace Explorer" });
  } else if (pathname.startsWith("/diagnosis")) {
    items.push({ title: "Diagnosis" });
  } else if (pathname.startsWith("/analytics")) {
    items.push({ title: "Analytics" });
  } else if (pathname.startsWith("/monitoring")) {
    items.push({ title: "Monitoring" });
  } else if (pathname.startsWith("/tasks/create")) {
    items.push({ title: <Link to="/tasks">Tasks</Link> });
    items.push({ title: "Create" });
  } else if (pathname.match(/^\/tasks\/[^/]+$/)) {
    items.push({ title: <Link to="/tasks">Tasks</Link> });
    items.push({ title: params.id ? `${params.id.slice(0, 8)}…` : "Detail" });
  } else if (pathname === "/tasks") {
    items.push({ title: "Tasks" });
  } else if (pathname.match(/^\/reports\/[^/]+$/)) {
    items.push({ title: <Link to="/reports">Reports</Link> });
    items.push({ title: "Detail" });
  } else if (pathname === "/reports") {
    items.push({ title: "Reports" });
  } else if (pathname === "/billing") {
    items.push({ title: "Billing" });
  } else if (pathname === "/plugins") {
    items.push({ title: "Plugins" });
  } else if (pathname === "/settings") {
    items.push({ title: "Settings" });
  }

  return items;
}

/** Compact breadcrumb for nested pages (hidden on dashboard). */
export function AppBreadcrumb() {
  const { pathname } = useLocation();
  const params = useParams();

  if (pathname === "/" || pathname === "/dashboard" || pathname === "/404") return null;

  const items = buildCrumbs(pathname, params);
  if (items.length <= 1) return null;

  return (
    <div className="af-no-print" style={{ marginBottom: 12 }}>
      <Breadcrumb className="ic-breadcrumb" items={items} />
    </div>
  );
}

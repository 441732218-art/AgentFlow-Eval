import { Breadcrumb } from "antd";
import { Link, useLocation, useParams } from "react-router-dom";
import { HomeOutlined } from "@ant-design/icons";

function buildCrumbs(pathname: string, params: Record<string, string | undefined>) {
  const items: Array<{ title: React.ReactNode }> = [
    {
      title: (
        <Link to="/">
          <HomeOutlined /> 总览
        </Link>
      ),
    },
  ];

  if (pathname.startsWith("/tasks/create")) {
    items.push({ title: <Link to="/tasks">任务</Link> });
    items.push({ title: "创建" });
  } else if (pathname.match(/^\/tasks\/[^/]+$/)) {
    items.push({ title: <Link to="/tasks">任务</Link> });
    items.push({ title: params.id ? `详情 ${params.id.slice(0, 8)}…` : "详情" });
  } else if (pathname === "/tasks") {
    items.push({ title: "任务列表" });
  } else if (pathname.match(/^\/reports\/[^/]+$/)) {
    items.push({ title: <Link to="/reports">报告</Link> });
    items.push({ title: "报告详情" });
  } else if (pathname === "/reports") {
    items.push({ title: "报告中心" });
  } else if (pathname === "/settings") {
    items.push({ title: "设置" });
  }

  return items;
}

/** Compact breadcrumb for nested pages (hidden on pure dashboard). */
export function AppBreadcrumb() {
  const { pathname } = useLocation();
  const params = useParams();

  if (pathname === "/" || pathname === "/404") return null;

  const items = buildCrumbs(pathname, params);
  if (items.length <= 1) return null;

  return (
    <div className="af-no-print" style={{ marginBottom: 12 }}>
      <Breadcrumb items={items} style={{ fontSize: 13 }} />
    </div>
  );
}

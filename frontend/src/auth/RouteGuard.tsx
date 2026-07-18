/* (c) 2026 AgentFlow-Eval */
import { Result, Button, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import type { Permission } from "./permissions";

type Props = {
  permission?: Permission | string;
  children: ReactNode;
};

/** Route-level guard — shows 403 when RBAC enforced and permission missing. */
export function RouteGuard({ permission, children }: Props) {
  const { loading, can, rbacEnforced } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div style={{ display: "grid", placeItems: "center", minHeight: 240 }}>
        <Spin />
      </div>
    );
  }

  if (permission && rbacEnforced && !can(permission)) {
    return (
      <Result
        status="403"
        title="403"
        subTitle="当前角色无权访问此页面"
        extra={
          <Button type="primary" onClick={() => navigate("/dashboard")}>
            返回总览
          </Button>
        }
      />
    );
  }

  return <>{children}</>;
}

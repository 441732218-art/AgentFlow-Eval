/* (c) 2026 AgentFlow-Eval */
import type { ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import type { Permission } from "./permissions";

type Props = {
  /** Required permission (or any of when array). */
  perm?: Permission | string | Array<Permission | string>;
  /** Optional fallback when denied. */
  fallback?: ReactNode;
  children: ReactNode;
};

/** Button / section-level permission gate. */
export function Can({ perm, fallback = null, children }: Props) {
  const { can, canAny, rbacEnforced } = useAuth();
  if (!perm || !rbacEnforced) return <>{children}</>;
  const ok = Array.isArray(perm) ? canAny(perm) : can(perm);
  return ok ? <>{children}</> : <>{fallback}</>;
}

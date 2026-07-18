/* (c) 2026 AgentFlow-Eval */
import { useAuth } from "./AuthProvider";
import type { Permission } from "./permissions";

export function usePermission() {
  const { can, canAny, permissions, role, rbacEnforced, loading } = useAuth();
  return { can, canAny, permissions, role, rbacEnforced, loading };
}

export function useCan(perm: Permission | string): boolean {
  return useAuth().can(perm);
}

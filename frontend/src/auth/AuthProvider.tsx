/* (c) 2026 AgentFlow-Eval */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiClient } from "@/api/client";
import { bootstrapApiKey } from "@/lib/bootstrap-api-key";
import type { MeResponse, Permission } from "./permissions";

type AuthState = {
  loading: boolean;
  actor: string;
  role: string;
  permissions: Set<string>;
  rbacEnforced: boolean;
  authEnabled: boolean;
  /** True when backend returns 401 / auth required and no valid session */
  needsApiKey: boolean;
  me: MeResponse | null;
  error: string | null;
  refresh: () => Promise<void>;
  can: (perm: Permission | string) => boolean;
  canAny: (perms: Array<Permission | string>) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

/** When /me fails (offline), allow all so demos still work. */
const OPEN_PERMS = new Set<string>([
  "task:create",
  "task:read",
  "task:update",
  "task:delete",
  "task:execute",
  "task:cancel",
  "evaluation:read",
  "evaluation:submit",
  "evaluation:approve",
  "user:manage",
  "system:config",
  "audit:read",
]);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsApiKey, setNeedsApiKey] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await apiClient.get<MeResponse>("/me");
      setMe(data);
      setError(null);
      setNeedsApiKey(false);
    } catch (e: unknown) {
      setMe(null);
      const msg = e instanceof Error ? e.message : "failed to load /me";
      setError(msg);
      const status =
        e && typeof e === "object" && "status" in e
          ? Number((e as { status?: number }).status)
          : undefined;
      // 401 = AUTH_ENABLED without valid key
      setNeedsApiKey(status === 401 || /未授权|Unauthorized|API [Kk]ey/i.test(msg));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      await bootstrapApiKey();
      if (!cancelled) await refresh();
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const permissions = useMemo(() => {
    if (me?.permissions?.length) return new Set(me.permissions);
    // Auth off or fetch failed → open (matches backend unrestricted local mode)
    // When needsApiKey, still return open perms so route guards don't 403 before gate
    return OPEN_PERMS;
  }, [me]);

  const rbacEnforced = Boolean(me?.rbac_enforced);
  const can = useCallback(
    (perm: Permission | string) => {
      if (!rbacEnforced) return true;
      return permissions.has(perm);
    },
    [permissions, rbacEnforced]
  );
  const canAny = useCallback(
    (perms: Array<Permission | string>) => perms.some((p) => can(p)),
    [can]
  );

  const value: AuthState = {
    loading,
    actor: me?.actor ?? "anonymous",
    role: me?.role ?? "admin",
    permissions,
    rbacEnforced,
    authEnabled: Boolean(me?.auth_enabled) || needsApiKey,
    // Show gate whenever /me returned 401 (missing or invalid API key)
    needsApiKey,
    me,
    error,
    refresh,
    can,
    canAny,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

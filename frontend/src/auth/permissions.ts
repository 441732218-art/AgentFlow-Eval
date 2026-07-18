/* (c) 2026 AgentFlow-Eval */
/** Permission strings — keep in sync with backend app.core.rbac.Permission */

export type Permission =
  | "task:create"
  | "task:read"
  | "task:update"
  | "task:delete"
  | "task:execute"
  | "task:cancel"
  | "evaluation:read"
  | "evaluation:submit"
  | "evaluation:approve"
  | "user:manage"
  | "system:config"
  | "audit:read";

/** All known permissions (contract tests can compare with backend). */
export const ALL_PERMISSIONS: Permission[] = [
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
];

export type MeResponse = {
  actor: string;
  role: string;
  permissions: string[];
  rbac_enforced: boolean;
  auth_enabled: boolean;
  billing_enabled?: boolean;
  deploy?: Record<string, unknown>;
  request_id?: string | null;
};

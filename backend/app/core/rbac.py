# (c) 2026 AgentFlow-Eval
"""Role-Based Access Control (RBAC) for AgentFlow-Eval.

Enterprise roles (v1.0)
-----------------------
system_admin, tenant_admin, manager, reviewer, member, viewer

Legacy aliases (still accepted)
-------------------------------
admin → system_admin, user → member, guest → viewer

Permissions
-----------
task:* | evaluation:* | user:manage | system:config | audit:read
tenant:create | tenant:manage | billing:read | billing:manage
benchmark:create | benchmark:read

API key format (``API_KEYS``)
-----------------------------
- ``secret``
- ``secret:actor``
- ``secret:actor:role``   e.g. ``sk-ops:alice:manager``

Optional ``ACTOR_ROLES=alice:manager,bob:user`` overrides / fills role when not
embedded in the key. Actors listed in ``ADMIN_ACTORS`` default to SYSTEM_ADMIN.
"""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import Awaitable, Callable, Collection
from enum import Enum
from typing import Any, ParamSpec, TypeVar, overload

from fastapi import Depends, Request

from app.config import settings
from app.utils.exceptions import AgentFlowError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Role(str, Enum):
    """Roles ordered from most to least privileged.

    Enterprise (canonical): system_admin, tenant_admin, manager, reviewer,
    member, viewer.

    Legacy members (admin/user/guest) remain for backward-compatible API keys
    and tests; they share permission sets with their enterprise equivalents.
    """

    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    MEMBER = "member"
    VIEWER = "viewer"
    # Legacy aliases (distinct enum members, same permission mapping)
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

    @classmethod
    def parse(cls, value: str | None, default: "Role | None" = None) -> "Role":
        """Parse a role string (case-insensitive); maps legacy names."""
        if value is None or not str(value).strip():
            if default is not None:
                return default
            raise ValueError("empty role")
        key = str(value).strip().lower().replace("-", "_")
        # Prefer enterprise names when both exist
        aliases = {
            "sysadmin": cls.SYSTEM_ADMIN,
            "systemadmin": cls.SYSTEM_ADMIN,
            "owner": cls.TENANT_ADMIN,
            "org_admin": cls.TENANT_ADMIN,
        }
        if key in aliases:
            return aliases[key]
        for role in cls:
            if role.value == key or role.name.lower() == key:
                return role
        raise ValueError(f"unknown role: {value!r}")

    def canonical(self) -> "Role":
        """Map legacy roles to enterprise names."""
        if self is Role.ADMIN:
            return Role.SYSTEM_ADMIN
        if self is Role.USER:
            return Role.MEMBER
        if self is Role.GUEST:
            return Role.VIEWER
        return self


class Permission(str, Enum):
    """Fine-grained permissions (resource:action)."""

    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    TASK_CANCEL = "task:cancel"

    EVALUATION_READ = "evaluation:read"
    EVALUATION_SUBMIT = "evaluation:submit"
    EVALUATION_APPROVE = "evaluation:approve"

    USER_MANAGE = "user:manage"
    SYSTEM_CONFIG = "system:config"
    AUDIT_READ = "audit:read"

    TENANT_CREATE = "tenant:create"
    TENANT_MANAGE = "tenant:manage"
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"
    BENCHMARK_CREATE = "benchmark:create"
    BENCHMARK_READ = "benchmark:read"


# ---------------------------------------------------------------------------
# Role → permission matrix
# ---------------------------------------------------------------------------

_ALL_TASK = frozenset(
    {
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_DELETE,
        Permission.TASK_EXECUTE,
        Permission.TASK_CANCEL,
    }
)
_ALL_EVAL = frozenset(
    {
        Permission.EVALUATION_READ,
        Permission.EVALUATION_SUBMIT,
        Permission.EVALUATION_APPROVE,
    }
)
_TENANT_OPS = frozenset({Permission.TENANT_MANAGE})
_BILLING = frozenset({Permission.BILLING_READ, Permission.BILLING_MANAGE})
_BENCHMARK = frozenset({Permission.BENCHMARK_CREATE, Permission.BENCHMARK_READ})

_SYSTEM_ADMIN_PERMS = frozenset(Permission)

_TENANT_ADMIN_PERMS = frozenset(
    {
        *_ALL_TASK,
        *_ALL_EVAL,
        Permission.AUDIT_READ,
        Permission.USER_MANAGE,
        *_TENANT_OPS,
        *_BILLING,
        *_BENCHMARK,
        # no system:config / tenant:create (platform-level)
    }
)

_MANAGER_PERMS = frozenset(
    {
        *_ALL_TASK,
        *_ALL_EVAL,
        Permission.AUDIT_READ,
        Permission.BILLING_READ,
        Permission.BENCHMARK_CREATE,
        Permission.BENCHMARK_READ,
    }
)

_REVIEWER_PERMS = frozenset(
    {
        Permission.TASK_READ,
        Permission.EVALUATION_READ,
        Permission.EVALUATION_SUBMIT,
        Permission.EVALUATION_APPROVE,
        Permission.AUDIT_READ,
        Permission.BENCHMARK_READ,
    }
)

_MEMBER_PERMS = frozenset(
    {
        *_ALL_TASK,
        Permission.EVALUATION_READ,
        Permission.EVALUATION_SUBMIT,
        Permission.BENCHMARK_READ,
        Permission.BILLING_READ,
    }
)

_VIEWER_PERMS = frozenset(
    {
        Permission.TASK_READ,
        Permission.EVALUATION_READ,
        Permission.BENCHMARK_READ,
    }
)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SYSTEM_ADMIN: _SYSTEM_ADMIN_PERMS,
    Role.TENANT_ADMIN: _TENANT_ADMIN_PERMS,
    Role.MANAGER: _MANAGER_PERMS,
    Role.REVIEWER: _REVIEWER_PERMS,
    Role.MEMBER: _MEMBER_PERMS,
    Role.VIEWER: _VIEWER_PERMS,
    # Legacy mirrors
    Role.ADMIN: _SYSTEM_ADMIN_PERMS,
    Role.USER: _MEMBER_PERMS,
    Role.GUEST: _VIEWER_PERMS,
}

# Roles that may access resources owned by other actors *within the same tenant*
CROSS_OWNER_ROLES: frozenset[Role] = frozenset(
    {
        Role.SYSTEM_ADMIN,
        Role.TENANT_ADMIN,
        Role.MANAGER,
        Role.REVIEWER,
        Role.ADMIN,  # legacy
    }
)

# Backward-compatible alias used by older code / docs
CROSS_TENANT_ROLES = CROSS_OWNER_ROLES


class ForbiddenError(AgentFlowError):
    """Permission denied (HTTP 403)."""

    def __init__(
        self,
        message: str = "Forbidden",
        detail: Any = None,
    ) -> None:
        super().__init__(message=message, status_code=403, detail=detail)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def rbac_enforced() -> bool:
    """Return True when RBAC permission checks must be applied.

    Requires both AUTH and RBAC flags so local Eager mode stays frictionless.
    """
    return bool(getattr(settings, "AUTH_ENABLED", False) and getattr(settings, "RBAC_ENABLED", True))


def default_role() -> Role:
    """Default role for authenticated actors without an explicit mapping."""
    raw = getattr(settings, "DEFAULT_ROLE", None) or "member"
    try:
        return Role.parse(str(raw), default=Role.MEMBER)
    except ValueError:
        return Role.MEMBER


def parse_actor_roles(raw: str | None = None) -> dict[str, Role]:
    """Parse ``ACTOR_ROLES`` config: ``alice:manager,bob:member``."""
    text = raw if raw is not None else getattr(settings, "ACTOR_ROLES", "") or ""
    mapping: dict[str, Role] = {}
    for part in str(text).split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        actor, role_s = part.split(":", 1)
        actor = actor.strip()
        try:
            mapping[actor] = Role.parse(role_s.strip())
        except ValueError:
            logger.warning("Ignoring invalid ACTOR_ROLES entry: %s", part)
    return mapping


def resolve_role_for_actor(actor: str, explicit: Role | None = None) -> Role:
    """Resolve role for an actor name.

    Priority: explicit (from API key) → ACTOR_ROLES → ADMIN_ACTORS → DEFAULT_ROLE.
    """
    if explicit is not None:
        return explicit
    from app.core.tenancy import admin_actors

    if actor in admin_actors():
        return Role.SYSTEM_ADMIN
    mapped = parse_actor_roles().get(actor)
    if mapped is not None:
        return mapped
    return default_role()


def permissions_for(role: Role) -> frozenset[Permission]:
    """Return the permission set granted to ``role``."""
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(
    role: Role | str | None,
    permission: Permission | str,
) -> bool:
    """Check whether ``role`` includes ``permission``."""
    if role is None:
        return False
    try:
        r = role if isinstance(role, Role) else Role.parse(str(role))
    except ValueError:
        return False
    try:
        p = permission if isinstance(permission, Permission) else Permission(str(permission))
    except ValueError:
        return False
    return p in permissions_for(r)


def has_any_permission(
    role: Role | str | None,
    permissions: Collection[Permission | str],
) -> bool:
    """True if role has at least one of the given permissions."""
    return any(has_permission(role, p) for p in permissions)


def has_all_permissions(
    role: Role | str | None,
    permissions: Collection[Permission | str],
) -> bool:
    """True if role has every given permission."""
    return all(has_permission(role, p) for p in permissions)


# ---------------------------------------------------------------------------
# Identity helpers (request-scoped)
# ---------------------------------------------------------------------------


def get_request_role(request: Request) -> Role:
    """Resolve the caller's role from request state / identity."""
    auth = getattr(request.state, "auth", None)
    if auth is not None and getattr(auth, "role", None) is not None:
        role = auth.role
        if isinstance(role, Role):
            return role
        try:
            return Role.parse(str(role))
        except ValueError:
            pass
    actor = getattr(request.state, "actor", None) or "anonymous"
    # Public health paths may set actor=public
    if actor in {"public", "anonymous"} and not rbac_enforced():
        return Role.SYSTEM_ADMIN  # unrestricted local mode
    if actor == "public":
        return Role.VIEWER
    return resolve_role_for_actor(actor)


def ensure_permission(
    role: Role | str | None,
    permission: Permission | str,
    *,
    message: str | None = None,
) -> None:
    """Raise :class:`ForbiddenError` if permission is missing (when RBAC on)."""
    if not rbac_enforced():
        return
    if has_permission(role, permission):
        return
    perm_s = permission.value if isinstance(permission, Permission) else str(permission)
    role_s = role.value if isinstance(role, Role) else str(role or "none")
    raise ForbiddenError(
        message or f"Missing permission: {perm_s}",
        detail={"required": perm_s, "role": role_s},
    )


def ensure_resource_access(
    *,
    role: Role | str | None,
    actor: str | None,
    owner: str | None,
    permission: Permission | str,
    resource: str = "Resource",
    resource_id: str = "",
    hide_existence: bool = True,
) -> None:
    """Permission + ownership check for a single resource.

    SYSTEM_ADMIN / TENANT_ADMIN / MANAGER / REVIEWER may cross *owners*
    within the same tenant for permitted actions.
    MEMBER / VIEWER are limited to resources they own (``owner == actor``).

    Args:
        role: Caller role.
        actor: Caller actor name.
        owner: Resource owner (e.g. task.created_by).
        permission: Required permission.
        resource: Resource type label for errors.
        resource_id: Resource id for errors.
        hide_existence: If True, deny with 404 instead of 403 for foreign rows.
    """
    ensure_permission(role, permission)

    if not rbac_enforced():
        return

    try:
        r = role if isinstance(role, Role) else Role.parse(str(role or "viewer"))
    except ValueError:
        r = Role.VIEWER

    if r in CROSS_OWNER_ROLES:
        return

    owner_s = (owner or "anonymous").strip() or "anonymous"
    actor_s = (actor or "anonymous").strip() or "anonymous"
    if owner_s == actor_s:
        return

    if hide_existence:
        from app.utils.exceptions import NotFoundError

        raise NotFoundError(resource, resource_id)
    raise ForbiddenError(
        f"Not allowed to access {resource}",
        detail={"resource_id": resource_id, "owner": owner_s},
    )


# ---------------------------------------------------------------------------
# Decorator (sync + async)
# ---------------------------------------------------------------------------


def _extract_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    if "request" in kwargs and isinstance(kwargs["request"], Request):
        return kwargs["request"]
    for a in args:
        if isinstance(a, Request):
            return a
    return None


def _check_permissions_on_request(
    request: Request | None,
    permissions: tuple[Permission | str, ...],
    *,
    require_all: bool,
) -> None:
    if request is None:
        if rbac_enforced():
            raise ForbiddenError(
                "Permission check requires Request in endpoint signature"
            )
        return
    role = get_request_role(request)
    if require_all:
        for perm in permissions:
            ensure_permission(role, perm)
        return
    if rbac_enforced() and not has_any_permission(role, permissions):
        raise ForbiddenError(
            "Missing one of required permissions",
            detail={
                "required_any": [
                    p.value if isinstance(p, Permission) else str(p) for p in permissions
                ],
                "role": role.value,
            },
        )


def _preserve_fastapi_signature(wrapper: Callable[..., Any], fn: Callable[..., Any]) -> None:
    """Copy resolved type hints onto the wrapper so FastAPI can introspect it.

    With ``from __future__ import annotations``, string annotations must be
    resolved against the *original* function globals. FastAPI reads
    ``inspect.signature`` annotations, so we rebuild the signature with
    concrete types (not ForwardRef strings).
    """
    from typing import get_type_hints

    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except Exception:
        hints = {}

    new_params: list[inspect.Parameter] = []
    for name, param in sig.parameters.items():
        ann = hints.get(name, param.annotation)
        new_params.append(param.replace(annotation=ann))
    ret = hints.get("return", sig.return_annotation)
    wrapper.__signature__ = sig.replace(  # type: ignore[attr-defined]
        parameters=new_params,
        return_annotation=ret,
    )
    ann_map: dict[str, Any] = {p.name: p.annotation for p in new_params}
    if ret is not inspect.Signature.empty:
        ann_map["return"] = ret
    wrapper.__annotations__ = ann_map


def require_permission(
    *permissions: Permission | str,
    require_all: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator enforcing one or more permissions.

    Works for both ``async def`` and plain ``def`` callables that receive a
    Starlette/FastAPI ``Request`` (as argument or ``request=`` kwarg).

    Args:
        permissions: Required permission(s).
        require_all: If True, all must be present; else any one is enough.
    """
    if not permissions:
        raise ValueError("require_permission() needs at least one permission")

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                request = _extract_request(args, kwargs)
                _check_permissions_on_request(
                    request, permissions, require_all=require_all
                )
                return await fn(*args, **kwargs)

            _preserve_fastapi_signature(async_wrapper, fn)
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(fn)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            request = _extract_request(args, kwargs)
            _check_permissions_on_request(
                request, permissions, require_all=require_all
            )
            return fn(*args, **kwargs)

        _preserve_fastapi_signature(sync_wrapper, fn)
        return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# FastAPI Depends factories
# ---------------------------------------------------------------------------


def RequirePermission(
    *permissions: Permission | str,
    require_all: bool = True,
) -> Any:
    """FastAPI dependency that enforces permissions and returns the role.

    Usage::

        @router.post("")
        async def create_task(
            request: Request,
            _role: Role = RequirePermission(Permission.TASK_CREATE),
        ):
            ...
    """

    async def _dependency(request: Request) -> Role:
        role = get_request_role(request)
        if require_all:
            for perm in permissions:
                ensure_permission(role, perm)
        else:
            if rbac_enforced() and not has_any_permission(role, permissions):
                raise ForbiddenError(
                    "Missing one of required permissions",
                    detail={
                        "required_any": [
                            p.value if isinstance(p, Permission) else str(p)
                            for p in permissions
                        ],
                        "role": role.value,
                    },
                )
        request.state.role = role
        return role

    return Depends(_dependency)


def matrix_as_dict() -> dict[str, list[str]]:
    """Export role→permission matrix for docs / settings API."""
    return {
        role.value: sorted(p.value for p in perms)
        for role, perms in ROLE_PERMISSIONS.items()
    }

# RBAC 权限控制

AgentFlow-Eval 在 API Key 鉴权之上提供基于角色的访问控制（RBAC）。

## 启用条件

| 配置 | 说明 |
|------|------|
| `AUTH_ENABLED=true` | 必须开启 API Key 鉴权 |
| `RBAC_ENABLED=true` | 默认 true；与 AUTH 同时开启时才强制校验权限 |
| `DEFAULT_ROLE` | 未指定角色时的默认角色，默认 `user` |
| `ACTOR_ROLES` | 可选映射 `alice:manager,bob:reviewer` |
| `ADMIN_ACTORS` | 仍映射为 **ADMIN** 角色（兼容旧配置） |

本地 Eager / 关闭鉴权时 **不强制 RBAC**，避免阻塞开发。

## 角色（5 种）

| 角色 | 说明 |
|------|------|
| `admin` | 全部权限 |
| `manager` | 任务/评测/审计，无用户管理与系统配置 |
| `reviewer` | 只读任务 + 评测读写/审批 + 审计只读 |
| `user` | 任务全生命周期 + 评测提交（无审批/审计/系统） |
| `guest` | 仅 `task:read`、`evaluation:read` |

## 权限清单

```
task:create | task:read | task:update | task:delete | task:execute | task:cancel
evaluation:read | evaluation:submit | evaluation:approve
user:manage | system:config | audit:read
```

### 角色-权限矩阵（摘要）

| 权限 | admin | manager | reviewer | user | guest |
|------|:-----:|:-------:|:--------:|:----:|:-----:|
| task:* | ✅ | ✅ | 读 | ✅ | 读 |
| evaluation:read | ✅ | ✅ | ✅ | ✅ | ✅ |
| evaluation:submit | ✅ | ✅ | ✅ | ✅ | ❌ |
| evaluation:approve | ✅ | ✅ | ✅ | ❌ | ❌ |
| audit:read | ✅ | ✅ | ✅ | ❌ | ❌ |
| user:manage | ✅ | ❌ | ❌ | ❌ | ❌ |
| system:config | ✅ | ❌ | ❌ | ❌ | ❌ |

完整列表见 `GET /api/v1/settings` 的 `role_matrix` 字段。

## API Key 格式

```bash
# secret only → actor=key_N, role=DEFAULT_ROLE
API_KEYS=dev-secret

# secret:actor
API_KEYS=dev-secret:alice

# secret:actor:role
API_KEYS=admin-key:root:admin,mgr-key:ops:manager,rev-key:r1:reviewer,user-key:u1:user,guest-key:g1:guest

# 或用 ACTOR_ROLES 补充
ACTOR_ROLES=alice:manager,bob:user
ADMIN_ACTORS=root,ops-admin
```

## 资源级控制

对 Task 等资源除权限点外，还校验 **归属**（`created_by`）：

| 角色 | 跨租户资源 |
|------|------------|
| admin / manager / reviewer | 允许（在已有权限前提下） |
| user / guest | 仅本人资源；越权返回 **404**（防枚举） |

## 代码用法

### 装饰器（async / sync）

```python
from app.core.rbac import Permission, require_permission

@router.post("")
@require_permission(Permission.TASK_CREATE)
async def create_task(request: Request, ...):
    ...
```

多权限默认 **全部满足**；`require_all=False` 表示任一即可。

### FastAPI Depends

```python
from app.core.rbac import Permission, RequirePermission, Role

@router.get("")
async def list_audit(
    role: Role = RequirePermission(Permission.AUDIT_READ),
):
    ...
```

### 资源检查

```python
from app.core.rbac import ensure_resource_access, Permission

ensure_resource_access(
    role=role,
    actor=actor,
    owner=task.created_by,
    permission=Permission.TASK_UPDATE,
    resource="Task",
    resource_id=task.id,
)
```

失败：缺权限 → **403**；越权资源（USER）→ **404**。

## 与端点映射（核心）

| 端点 | 权限 |
|------|------|
| `POST /tasks` | task:create |
| `GET /tasks` | task:read |
| `DELETE /tasks/{id}` | task:delete |
| `POST .../execute` | task:execute |
| `POST .../cancel` | task:cancel |
| `POST .../test-suites*` | task:update |
| `POST /traces/{id}/judge` | evaluation:submit |
| `POST /traces/{id}/review` | evaluation:approve |
| `GET /reports/{id}` | evaluation:read |
| `GET /audit` | audit:read |
| `POST /tools/probe` | system:config |

## 身份接口

`GET /api/v1/settings/actor` 返回：

- `role` / `permissions`
- `rbac_enabled` / `auth_enabled`
- 既有 `current_actor`、`is_admin` 等字段

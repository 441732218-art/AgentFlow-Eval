# Enterprise RBAC — AgentFlow-Eval v1.0

> 与实现源码对齐：`backend/app/core/rbac.py`  
> 前端权限字符串：`frontend/src/auth/permissions.ts`

---

## 1. 角色（Roles）

| 角色 | 值 | 说明 |
|------|-----|------|
| **System Admin** | `system_admin` | 平台超管；跨租户；可 `tenant:create` |
| **Tenant Admin** | `tenant_admin` | 租户管理员；成员/计费/评测全权（租户内） |
| **Manager** | `manager` | 评测运营；审计读；计费读；Benchmark 创建 |
| **Reviewer** | `reviewer` | 评审批准；只读任务 |
| **Member** | `member` | 日常评测创建/执行 |
| **Viewer** | `viewer` | 只读 |

### 1.1 遗留别名（兼容）

| 旧值 | 映射权限同 |
|------|------------|
| `admin` | `system_admin` |
| `user` | `member` |
| `guest` | `viewer` |

API Key 仍可写 `secret:alice:admin`；`Role.parse` 与权限矩阵双轨支持。

---

## 2. 权限矩阵（Permission Matrix）

| Permission | system_admin | tenant_admin | manager | reviewer | member | viewer |
|------------|:---:|:---:|:---:|:---:|:---:|:---:|
| task:create/read/update/delete/execute/cancel | ✅ | ✅ | ✅ | 读 | ✅ | 读 |
| evaluation:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| evaluation:submit | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| evaluation:approve | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| audit:read | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| user:manage | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| system:config | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tenant:create | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tenant:manage | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| billing:read | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| billing:manage | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| benchmark:create | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| benchmark:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

完整枚举以 `Permission` / `ROLE_PERMISSIONS` 为准；`GET /api/v1/me` 返回当前权限列表。

---

## 3. 作用域

| 范围 | 规则 |
|------|------|
| **跨 Owner（同租户）** | `system_admin` / `tenant_admin` / `manager` / `reviewer`（及 legacy `admin`） |
| **仅本人** | `member` / `viewer`（及 legacy `user` / `guest`） |
| **跨租户** | 仅 `system_admin`（及 `admin`）；需 `X-Tenant-ID` 切换上下文 |

多租户开关：`MULTI_TENANT_ENABLED=true`。  
请求头：`X-Tenant-ID: <uuid|slug>`。

---

## 4. API Key 绑定角色

```env
API_KEYS=af-root:ops:system_admin,af-ta:alice:tenant_admin,af-dev:bob:member
ACTOR_ROLES=alice:tenant_admin,bob:member
ADMIN_ACTORS=ops
DEFAULT_ROLE=member
```

---

## 5. 与 Lite / Private / SaaS

| Profile | 建议 |
|---------|------|
| **lite** | `AUTH_ENABLED=false` → 运行时等价 system_admin，无摩擦 |
| **private** | API Key + 可选 `MULTI_TENANT_ENABLED`（多团队） |
| **saas** | `AUTH_ENABLED=true` + `MULTI_TENANT_ENABLED=true` + Billing |

---

## 6. 测试

- `tests/unit/test_rbac.py` — 基础矩阵  
- `tests/unit/test_rbac_enterprise.py` — 企业角色与新权限  
- `tests/unit/test_tenant_isolation.py` — 租户隔离  

---

*文档版本：v1.0 阶段 4*

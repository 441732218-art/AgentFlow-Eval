# SaaS 计费基础（Billing）

Feature Flag：`BILLING_ENABLED=false` 时配额门闩与计量落库为 **no-op / 软记录**，不影响现有私有化部署。

## 表结构

| 表 | 用途 |
|----|------|
| `billing_plans` | 套餐目录（free / pro / enterprise 种子） |
| `subscriptions` | 用户/租户订阅 |
| `usage_records` | 用量事件（token / task / judge） |
| `quota_balances` | 按月额度计数 |
| `invoices` | 账单草稿 |

迁移：`alembic/versions/010_billing.py`

## 套餐（Free / Pro / Enterprise）

| 套餐 | 任务 | Token | Storage (MB) | Plugins | 价格 |
|------|------|-------|--------------|---------|------|
| free | 50 | 50k | 500 | 4 | $0 |
| pro | 1000 | 1M | 10k | 50 | $49/mo |
| enterprise | 100k | 100M | 1M | 10k | custom |

限额字段：`task_quota` / `token_quota` / `storage_quota_mb` / `plugin_quota`（migration `014`）。

## API

```
GET  /api/v1/billing/plans
GET  /api/v1/billing/plan          # 当前套餐 + quota 快照
GET  /api/v1/billing/quota
GET  /api/v1/billing/usage
POST /api/v1/billing/subscribe     { "plan_code": "pro" }
POST /api/v1/billing/checkout
POST /api/v1/billing/webhook       # Stripe 兼容别名
POST /api/v1/billing/webhook/stripe
GET  /api/v1/billing/invoices
POST /api/v1/billing/invoices/draft
```

## 挂钩

- `POST /tasks/{id}/execute` → `ensure_task_quota`（仅 BILLING_ENABLED）+ `record_usage(metric=task)`
- `observe_suite_run` / `observe_judge` → `MeteringPort.record`（token/judge），**actor = Task.created_by**
- 超额：HTTP **429** + `detail.code = QUOTA_EXCEEDED`（前端提示额度超限）

## 账期重置

```
POST /api/v1/billing/quota/rollover
POST /api/v1/billing/quota/rollover?all_actors=true
```

为当前 `YYYY-MM` 创建新的 `quota_balances`（计数归零，limit 来自套餐）。幂等。

## 启用

```env
BILLING_ENABLED=true
DEPLOY_PROFILE=saas
```

```bash
cd backend && alembic upgrade head
```

## 演示：额度打满 → 402

1. `BILLING_ENABLED=true`
2. 将当前 actor 的 `task_used` 调到 `task_limit`（或订阅 free 后压测）
3. `POST /tasks/{id}/execute` → **402 Quota exceeded**
4. 订阅 pro / 调用 rollover → 可继续执行

## Stripe Checkout 占位

默认 **mock**（不产生真实扣款）。

| 变量 | 说明 |
|------|------|
| `STRIPE_MODE` | `mock`（默认）或 `live` |
| `STRIPE_SECRET_KEY` | live 模式 sk_… |
| `STRIPE_WEBHOOK_SECRET` | whsec_… |
| `STRIPE_PRICE_IDS` | `pro:price_xxx,enterprise:price_yyy` |
| `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` | 回跳前端 |

### API

```
POST /api/v1/billing/checkout          { "plan_code": "pro" }  → { checkout: { url, session_id, mode } }
POST /api/v1/billing/checkout/mock-confirm  { session_id, plan_code }  # 仅 mock
POST /api/v1/billing/webhook/stripe    # 公网 webhook（签名校验；mock 跳过）
```

### 前端

用量页对 **付费套餐** 走 Checkout：mock 下自动 `mock-confirm` 激活；live 下 `window.location` 跳转 Stripe。

### Live 上线清单

1. `pip install stripe`
2. `STRIPE_MODE=live` + Secret / Webhook secret / Price IDs
3. Stripe Dashboard webhook → `https://your-api/api/v1/billing/webhook/stripe`  
   事件：`checkout.session.completed`

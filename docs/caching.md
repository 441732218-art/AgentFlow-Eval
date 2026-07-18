# 多层级缓存架构

AgentFlow-Eval 使用 **L1 进程内存 + L2 Redis** 双层缓存，默认 **Cache-Aside**，创建/更新路径辅以 **Write-Through**。

## 架构

```
API Request
    │
    ▼
┌─────────────┐  hit   ┌──────────┐
│ L1 Memory   │ ─────► │ Response │
│ (OrderedDict│        └──────────┘
│  + TTL LRU) │
└──────┬──────┘ miss
       ▼
┌─────────────┐  hit   ┌──────────┐
│ L2 Redis    │ ─────► │ Response │  (+ 回填 L1)
│ redis.asyncio│        └──────────┘
└──────┬──────┘ miss
       ▼
   DB / 计算  ── write ──► L1 + L2
```

Redis 不可用时自动降级为仅 L1 / 直查 DB，**不阻塞业务**。

## TTL 策略

| 场景 | TTL | 策略 | 失效 |
|------|-----|------|------|
| 任务详情 | **5 min** | Cache-Aside + 写穿 | 主动 `invalidate_task` |
| 任务列表 | **30 s** | Cache-Aside + **版本号** | 递增 `list_ver:{actor}` |
| 仪表板统计 | **1 min** | Cache-Aside | 任务变更时删 key |
| 评估结果 | **1 h** | Cache-Aside **版本化** | 重评/人工复核删 pattern |
| 系统配置 | **10 min** | Cache-Aside | `invalidate_settings` |

Key 前缀：`af:`（AgentFlow）。

示例：

```
af:task:detail:{task_id}
af:task:list_ver:{actor}
af:task:list:{actor}:{ver}:{page}:{size}:{status}:{archived}
af:dashboard:stats:{actor}
af:eval:result:{trace_id}:{version}
af:settings:public
```

## 配置

```bash
CACHE_ENABLED=true
CACHE_WARMUP_ON_STARTUP=false   # true 时 lifespan 预热 settings/dashboard/list
REDIS_URL=redis://localhost:6379/0
```

## API 集成

| 端点 | 缓存行为 |
|------|----------|
| `GET /api/v1/tasks` | 列表 30s + 版本依赖 |
| `GET /api/v1/tasks/{id}` | 详情 5min |
| `POST/DELETE/.../execute/archive...` | 失效详情 + bump 列表版本 + 仪表板 |
| `GET /api/v1/dashboard/stats` | 仪表板 1min（新建） |
| `GET /api/v1/settings` | 配置 10min |
| `POST /api/v1/traces/{id}/judge` | 已有分数时版本化 1h；写入后失效旧版本 |

## 代码入口

```python
from app.core.cache import get_cache, cached, invalidate_task
from app.core.cache.keys import CacheTTL, task_detail_key

cache = get_cache()
await cache.get_or_set(task_detail_key(tid), factory, ttl=CacheTTL.TASK_DETAIL)

@cached(ttl=CacheTTL.SETTINGS, key_builder=lambda: "af:settings:public")
async def load_settings(): ...
```

领域服务：`app/core/cache/services.py`  
失效：`app/core/cache/invalidation.py`  
预热：`app/core/cache/warmup.py` → `warm_cache()`

兼容旧 API：`app.core.dependencies.cache_get/set/invalidate` 已委托到新客户端。

## 监控（Prometheus）

| 指标 | 含义 |
|------|------|
| `agentflow_cache_hits_total{layer=l1\|l2}` | 命中 |
| `agentflow_cache_misses_total` | 未命中 |
| `agentflow_cache_sets_total` | 写入 |
| `agentflow_cache_invalidations_total` | 删除/失效 key 数 |

命中率：

```promql
sum(rate(agentflow_cache_hits_total[5m]))
/
(sum(rate(agentflow_cache_hits_total[5m])) + sum(rate(agentflow_cache_misses_total[5m])))
```

## 预热

```bash
CACHE_WARMUP_ON_STARTUP=true
```

或代码：

```python
from app.core.cache.warmup import warm_cache
await warm_cache(actor="anonymous", limit=20)
```

## 测试

```bash
cd backend
pytest tests/unit/test_cache.py tests/unit/test_cache_layer.py -q
```

## 运维注意

1. 列表依赖 **版本号** 而非 SCAN 全删，避免生产 KEYS 阻塞。
2. 多 worker 时 L1 不共享；L2 Redis 保证最终一致（短 TTL 可接受）。
3. 缓存 value 必须可 JSON 序列化（datetime 用 `default=str`）。

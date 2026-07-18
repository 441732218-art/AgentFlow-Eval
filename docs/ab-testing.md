# A/B 测试框架（Phase 3.5）

在线 A/B 与离线 **Experiments** 互补：

| | Offline Experiments | Online A/B |
|--|---------------------|------------|
| 场景 | 固定用例集上对比 Agent 配置 | 流量分流、持续收集转化/指标 |
| 执行 | 一次性 Celery 流水线 | sticky assign + event track |
| 输出 | 均分 / best label | 转化率、lift、p-value、winner |
| API | `/api/v1/experiments` | `/api/v1/ab` |

## 概念

- **Experiment**：可运行的 A/B 定义（key、状态、α、最小样本量）
- **Variant**：流量臂 + `weight` + `payload`（如 `agent_config`）
- **Assignment**：`unit_id`（用户/会话）→ 变体，**粘性哈希**
- **Event**：`exposure` | `conversion` | `metric`

状态机：`draft` → `running` ⇄ `paused` → `completed` / `archived`

## 分流算法

```
bucket = SHA256(experiment_key + "::" + unit_id) % 10000
position = (bucket / 10000) * sum(weights)
→ 落入累计权重区间的 variant
```

同一 `unit_id` 永远得到同一变体。

## 统计

| 指标类型 | 检验 |
|----------|------|
| 转化率 | 双样本比例 z 检验 + 95% CI（绝对 lift） |
| 连续值（score/latency） | Welch t 检验 |
| 样本量估算 | `POST /ab/sample-size` |

默认 `alpha=0.05`，`min_sample_size` 满足后才建议 `winner_variant_key`。

## API 速查

```
POST   /api/v1/ab                      创建（≥2 variants）
GET    /api/v1/ab                      列表
GET    /api/v1/ab/{id}                 详情
PATCH  /api/v1/ab/{id}/status          draft|running|paused|completed|archived
POST   /api/v1/ab/{key}/assign         分流 + 可选 exposure
POST   /api/v1/ab/{key}/track          exposure|conversion|metric
GET    /api/v1/ab/{id}/results         显著性分析
POST   /api/v1/ab/sample-size          样本量建议
POST   /api/v1/ab/from-offline/{expId} 从离线 Experiment 生成 AB draft
```

### 创建示例

```json
POST /api/v1/ab
{
  "key": "judge_prompt_v3",
  "name": "Judge prompt AB",
  "start_immediately": true,
  "min_sample_size": 200,
  "primary_metric": "conversion",
  "variants": [
    {
      "key": "control",
      "is_control": true,
      "weight": 1,
      "payload": { "agent_config": { "model": "gpt-4o-mini" } }
    },
    {
      "key": "treatment",
      "weight": 1,
      "payload": { "agent_config": { "model": "gpt-4o" } }
    }
  ]
}
```

### 客户端接入

```python
# 1) 分流
assign = POST /ab/judge_prompt_v3/assign {"unit_id": user_id}
config = assign["payload"]  # 应用 agent_config / feature flags

# 2) 曝光（assign 时可 record_exposure=true）
# 3) 转化
POST /ab/judge_prompt_v3/track {
  "unit_id": user_id,
  "event_type": "conversion"
}

# 4) 连续指标
POST /ab/judge_prompt_v3/track {
  "unit_id": user_id,
  "event_type": "metric",
  "metric_name": "score",
  "metric_value": 92.5
}
```

## 与离线实验联动

```
POST /api/v1/ab/from-offline/{offline_experiment_id}?key=my_ab_key
```

将每个 offline run 的 `label` + `agent_config` 变为等权 variants，状态 `draft`，人工确认后 `PATCH .../status` → `running`。

## 权限

| 操作 | 权限 |
|------|------|
| 创建 / 从 offline 提升 | `task:create` |
| 列表 / 详情 / assign / sample-size | `task:read` |
| track / 改状态 | `task:update` |
| results | `evaluation:read` |

## 数据表

迁移 `009_ab_tests`：

- `ab_experiments`
- `ab_variants`
- `ab_assignments`
- `ab_events`

```bash
cd backend && alembic upgrade head
```

## 代码

| 路径 | 说明 |
|------|------|
| `app/core/ab/assignment.py` | 粘性分流 |
| `app/core/ab/stats.py` | z 检验 / Welch t / 样本量 |
| `app/core/ab/service.py` | assign / track / analyze |
| `app/api/v1/endpoints/ab.py` | REST |
| `app/models/ab_test.py` | ORM |

## 测试

```bash
pytest tests/unit/test_ab_stats.py tests/unit/test_ab_api.py -q
```

# HTTP Agent Protocol — agentflow.http.v1

> 产品契约文档（Runner 统一接口 + Probe + SSRF）。  
> 实现：`backend/app/core/agent_runner/{protocol,http_runner,ssrf}.py` · UI：创建任务 → Runner=HTTP。

## 目标

让用户托管的 Agent 服务通过 **HTTP JSON** 接入 AgentFlow-Eval 的任务执行与 Trace 体系，无需改平台核心流水线。

**产品入口：** 前端「创建任务」选择 HTTP Runner → 可选「探测 Agent」→ 提交后走与 OpenAI 相同的评测流水线。

## 任务侧配置（`Task.agent_config`）

```json
{
  "runner": "http",
  "endpoint_url": "https://agent.example.com/v1/invoke",
  "timeout_sec": 60,
  "method": "POST",
  "headers": { "Authorization": "Bearer <token>" },
  "context": { "tenant": "acme" },
  "verify_ssl": true
}
```

别名：`runner` 可为 `http` | `http_agent` | `remote` | `webhook`。  
URL 字段：`endpoint_url` | `url` | `endpoint`。

## 请求（平台 → 你的 Agent）

`POST {endpoint_url}`  
`Content-Type: application/json`

```json
{
  "protocol_version": "agentflow.http.v1",
  "query": "用户 / 测试用例问题",
  "tools": ["web_search", "calculator"],
  "context": {},
  "meta": {
    "protocol_version": "agentflow.http.v1"
  }
}
```

| 字段 | 说明 |
|------|------|
| `query` | 当前 suite 的 `user_query` |
| `tools` | 期望工具名列表（由用例 `expected_tools` 解析） |
| `context` | 任务配置中的透传 JSON |
| `meta` | 平台元数据（后续可含 task_id / suite_id） |

## 响应（你的 Agent → 平台）

### 推荐：完整形态

```json
{
  "status": "success",
  "final_answer": "……",
  "steps": [
    {
      "iteration": 0,
      "thought": "…",
      "action": "calculator",
      "action_input": "1+1",
      "observation": "2",
      "tokens": 10
    }
  ],
  "total_tokens": 120,
  "response_time_ms": 800,
  "error_message": ""
}
```

`status` 取值：`success` | `failed` | `max_iterations_reached`。

### 兼容：短形态

```json
{ "answer": "……" }
```

或 `{ "output": "…" }` / `{ "final_answer": "…" }` / `{ "result": "…" }`。

### 兼容：纯文本

`Content-Type: text/plain`，body 即为最终答案。

若缺少 `steps`，平台会合成一条 `action=final_answer` 的步骤，以便 Trace / Judge 正常工作。

## 错误行为

| 情况 | 平台行为 |
|------|----------|
| HTTP ≥ 400 | Trace `failed`，`error_message` 含状态码与 body 摘要 |
| 超时 | `failed`，超时说明 |
| 网络错误 | `failed` |
| 无法解析的类型 | `failed` |

## Runner 统一调用约定（Phase 0）

所有 Runner（OpenAI / HTTP / 插件）统一为：

```python
result = await runner.run(
    query,
    tools=tools,                 # optional
    agent_config=agent_config,   # optional keyword-only
)
# result: dict | AgentResult → pipeline 用 ensure_pipeline_result() 归一
```

实现位置：

- `BaseAgentRunner` / `ensure_pipeline_result` → `agent_runner/base.py`
- Celery `run_single_test_suite` → 单路径调用，无 TypeError 双分支

## Probe API（Phase 1）

| Method | Path | 说明 |
|--------|------|------|
| `GET` | `/api/v1/agents/http/contract` | 协议摘要 |
| `POST` | `/api/v1/agents/http/probe` | 探测外部 Agent（SSRF + 可达性 + normalize） |

Probe 请求体示例：

```json
{
  "endpoint_url": "https://agent.example.com/v1/invoke",
  "timeout_sec": 10,
  "headers": {},
  "query": "ping"
}
```

## SSRF 防护

默认禁止：

- `file://` / `gopher://` / 非 http(s) scheme  
- `localhost` / `127.0.0.1` / `::1`  
- 私网：`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`  
- 链路本地 / 云 metadata（如 `169.254.169.254`）  

开发/测试可设环境变量：`HTTP_AGENT_ALLOW_PRIVATE_IP=true`（**勿在生产开启**）。

实现：`backend/app/core/agent_runner/ssrf.py`（`HttpAgentRunner` 与 Probe 共用）。

## 本地自检

```bash
cd backend
pytest tests/unit/test_agent_protocol.py tests/unit/test_http_runner.py tests/unit/test_ssrf.py tests/unit/test_agents_http_probe.py -q
```

## 版本

| 版本 | 说明 |
|------|------|
| `agentflow.http.v1` | 当前冻结：query/tools/context/meta + 上述响应兼容 |

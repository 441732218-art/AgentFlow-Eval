# 插件系统

AgentFlow-Eval 支持通过 **插件** 扩展 Agent 执行器、评估器、沙箱工具与流水线钩子，无需改核心代码即可接入第三方能力。

## 架构

```
PluginManager
 ├── discover (目录 / module:Class)
 ├── load → on_load
 ├── activate → on_activate  ──► CapabilityRegistry (runner / judge / tool)
 │                            └► HookRegistry (pre/post hooks)
 ├── deactivate → 注销能力
 └── unload → on_unload
```

| 插件类型 | 注册方式 | 使用入口 |
|----------|----------|----------|
| **AgentRunner** | `ctx.register_runner(key, factory)` | `agent_config.runner = key` |
| **Judge** | `ctx.register_judge(key, factory)` | `build_llm_judge({"type": key})` |
| **Tool** | `ctx.register_tool(name, fn, ...)` | 沙箱 `run_tool_sandboxed` / 用例 expected_tools |
| **Hook** | `ctx.register_hook(name, cb, priority=)` | 流水线自动 `emit` |

## 配置

| 环境变量 | 说明 | 默认 |
|----------|------|------|
| `PLUGINS_ENABLED` | 启动时是否加载插件 | `true` |
| `PLUGIN_DIRS` | 扫描目录（逗号分隔） | `plugins` |
| `PLUGIN_MODULES` | 显式入口 `pkg.mod:Plugin,...` | 空 |
| `PLUGIN_CATALOG_PATH` | 本地市场 catalog JSON | 空 |
| `PLUGIN_MARKET_SEED_EXAMPLES` | 是否注入示例目录 | `true` |

示例 `.env`：

```env
PLUGINS_ENABLED=true
PLUGIN_MODULES=app.plugins.examples.echo_tool:Plugin,app.plugins.examples.echo_runner:Plugin
PLUGIN_DIRS=./plugins
```

## 生命周期

状态机：`discovered` → `loaded` → `active` ⇄ `disabled` → `unloaded`；失败为 `error`。

| 方法 | 时机 |
|------|------|
| `on_load` | 导入并实例化后 |
| `on_activate` | 注册 runner/judge/tool/hook |
| `on_deactivate` | 注销能力，实例可保留 |
| `on_unload` | 丢弃实例前 |

## 钩子（Hooks）

内置事件（按 `priority` 升序执行；异常默认隔离）：

| 名称 | 触发点 |
|------|--------|
| `pre_agent_run` / `post_agent_run` | Celery 单用例执行前后 |
| `pre_judge` / `post_judge` | 评分前后 |
| `pre_tool` / `post_tool` | 沙箱工具执行前后（`pre` 可返回改写后的 `args`） |
| `task_created` / `task_completed` | 预留业务事件 |
| `plugin_loaded` / `plugin_unloaded` | 插件生命周期 |

```python
def on_activate(self, ctx: PluginContext) -> None:
    def log_pre(payload: dict):
        ctx.logger.info("agent start %s", payload.get("query"))
        return payload
    ctx.register_hook("pre_agent_run", log_pre, priority=50)
```

## 编写插件

### 最小模板

```python
from app.core.plugins.base import BasePlugin, PluginMeta, PluginType, PluginContext

class Plugin(BasePlugin):
    meta = PluginMeta(
        name="my_plugin",
        version="1.0.0",
        plugin_type=PluginType.TOOL,  # agent_runner | judge | tool | hook
        description="...",
        author="you",
        provides=["my_tool"],
    )

    def on_activate(self, ctx: PluginContext) -> None:
        ctx.register_tool(
            "my_tool",
            lambda **kw: "ok",
            description="My tool",
            parameters={"q": {"type": "string"}},
            required=["q"],
        )
```

### 目录形态

```
plugins/my_plugin/
  plugin.json      # name, version, type, entry(可选)
  plugin.py        # class Plugin(BasePlugin)
```

### 仓库内示例

| 入口 | 类型 |
|------|------|
| `app.plugins.examples.echo_tool:Plugin` | Tool `echo` |
| `app.plugins.examples.echo_runner:Plugin` | Runner `echo` / `echo_runner` |
| `app.plugins.examples.length_judge:Plugin` | Judge `length` |
| `app.plugins.examples.audit_hooks:Plugin` | Hook 审计日志 |

## API

前缀：`/api/v1/plugins`（写操作需 `system:config`）

```
GET    /plugins                 列表
GET    /plugins/status          能力摘要
GET    /plugins/hooks           已注册钩子
GET    /plugins/market          本地市场目录
POST   /plugins/market/install  { "catalog_id": "echo_tool" }
POST   /plugins/market/uninstall
POST   /plugins/load            { "entry": "pkg:Plugin" } 或 { "path": "..." }
GET    /plugins/{id}
POST   /plugins/{id}/activate
POST   /plugins/{id}/deactivate
POST   /plugins/{id}/reload
DELETE /plugins/{id}
```

### 任务侧使用插件 Runner

创建任务时：

```json
{
  "agent_config": {
    "runner": "echo",
    "prefix": "ECHO: "
  }
}
```

### 插件 Judge

```python
from app.core.celery_app.tasks import build_llm_judge
judge = build_llm_judge({"type": "length"})
```

## 商业化运营

| 能力 | 说明 |
|------|------|
| 市场目录 | `GET /plugins/market`（含 `is_paid` / `entitled`） |
| 付费 mock | `premium_length_judge`（$19.99，仅 pro/enterprise） |
| 权益硬校验 | `enforce_plugin_install`：commerce + plan.features + sandbox 权限 |
| 沙箱 | `PluginSandboxPolicy`；RBAC 开启时校验 `permissions[]` |
| 审计 | `plugin.install|uninstall|activate|deactivate|load|unload` |
| 前端 | `/plugins` 管理页（需 `system:config`） |

套餐 `features.plugins`：
- free：白名单示例插件
- pro/enterprise：`["*"]` 含付费 mock

## 安全说明

- 插件与主进程同权限；**仅加载可信来源**。
- 工具仍走沙箱超时与输出截断；`network=True` 仅作元数据标记，不自动放行外网。
- 生产环境建议：

```env
PLUGINS_ENABLED=true
PLUGIN_STRICT_ALLOWLIST=true
PLUGIN_MODULES=app.plugins.examples.echo_tool:Plugin
PLUGIN_DIRS=
PLUGIN_ALLOWLIST=app.plugins.examples.echo_tool
```

`PLUGIN_STRICT_ALLOWLIST=true` 时 **禁止扫描目录**，仅加载 `PLUGIN_MODULES`；`PLUGIN_ALLOWLIST` 可再收紧入口前缀。

## 测试

```bash
cd backend
pytest tests/unit/test_plugins.py tests/unit/test_plugin_entitlement.py -q
```

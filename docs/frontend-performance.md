# 前端性能优化（Phase 3.3）

面向 React 18 + Vite + React Query 的 AgentFlow-Eval 前端性能实践。

## 目标

| 指标 | 手段 |
|------|------|
| 首屏 JS 体积 | 路由懒加载 + vendor `manualChunks` |
| 列表/总览请求 | 对齐后端缓存 TTL；仪表板走 `/dashboard/stats` |
| 重渲染 | `memo` / 稳定回调 / React Flow `nodeTypes` 常量 |
| 导航体感 | 侧栏 hover **prefetch** 懒路由 chunk |

## 1. 构建分包（Vite）

`frontend/vite.config.ts`：

- `vendor-react` / `vendor-antd` / `vendor-charts` / `vendor-flow` / `vendor-export` …
- `cssCodeSplit: true`、`target: es2020`
- `optimizeDeps.include` 预构建高频依赖

验证：

```bash
cd frontend && npm run build
# dist/assets 中应看到多个 vendor-*.js
```

## 2. 路由级代码分割

`src/router/index.tsx` 已对页面使用 `React.lazy` + `Suspense` + `PageSkeleton`。

侧栏 hover/focus 时调用 `prefetchRoute`（`src/lib/performance.ts`）预加载对应 chunk。

## 3. React Query 与后端缓存对齐

| 查询 | `staleTime` | 后端缓存 |
|------|-------------|---------|
| 任务列表 | 30s | list 30s |
| 任务详情 | 5min | detail 5min |
| 仪表板 | 1min | dashboard 1min |
| 报告 | 2min | — |
| 默认 | 2min | — |

`gcTime` 15min；`structuralSharing: true`；列表 `keepPreviousData` 翻页不闪白。

变更任务后统一 `invalidateQueries(tasks + dashboard)`。

## 4. 仪表板数据路径

**之前**：`useTasks({ page_size: 50 })` 客户端聚合（大列表、统计不准）。

**现在**：

- `GET /api/v1/dashboard/stats` → `useDashboardStats`
- 最近任务仅拉 `page_size: 8`
- `StatCard` / `RecentTaskRow` 使用 `memo`

## 5. 组件层

| 组件 | 优化 |
|------|------|
| `TaskCard` | `React.memo` |
| `AgentStepNode` / `TraceFlowChart` | `memo`；`nodeTypes` 模块级常量 |
| `Sidebar` menu items | `useMemo`；hover prefetch |

## 6. 工具函数

`src/lib/performance.ts`：`debounce` / `throttle` / `scheduleIdle` / `prefetchRoute` / `ROUTE_PREFETCH`。

## 验收清单

```bash
cd frontend
npm run test          # 含 performance.test.ts
npm run build         # 分包成功
npm run type-check
```

建议用 Lighthouse / Network：

1. 首访 `/`：主包变小，charts/antd 分 chunk  
2. 再次进入 Dashboard：React Query 命中 stale 窗口，无重复 stats 请求（1 分钟内）  
3. hover「任务」后点击：chunk 已在后台加载  

## 后续可选

- 超长表格：`@tanstack/react-virtual` 窗口化  
- `React.lazy` 对 `html2canvas`/`jspdf` 仅在导出时动态 import（已在 vendor-export 分包）  
- 接入 Web Vitals 上报到现有 `/metrics` 旁路  

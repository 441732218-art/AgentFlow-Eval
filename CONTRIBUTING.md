# 贡献指南

感谢关注 AgentFlow-Eval！本文说明如何本地运行、提交 Issue 与 Pull Request。

## 行为准则

请保持友善与建设性讨论。恶意内容、骚扰或提交密钥等敏感信息将被拒绝。

## 开发环境

### 最小路径（Eager，无需 Redis）

1. 克隆仓库并进入目录  
2. 按 README「方式 B」启动后端与前端  
3. 可选：`cd backend && python -m app.core.seed` 写入演示数据  

### 完整路径（Docker）

1. 安装 Docker Desktop  
2. `scripts/generate-deploy-env.ps1` 或复制 `backend/.env.docker.example` → `.env.docker`  
3. 填写 `OPENAI_API_KEY`  
4. `scripts/docker-up.ps1` 或 `docker compose --env-file .env.docker up -d --build`  

## 分支与提交

- 从 `main` 拉取功能分支：`feat/xxx`、`fix/xxx`、`docs/xxx`  
- 提交信息建议：`type: 简短中文或英文说明`  
  - 类型：`feat` / `fix` / `docs` / `test` / `chore` / `refactor`  
- 一个 PR 尽量只做一件事  

## 代码规范

### 后端（`backend/`）

- Python 3.11+，格式与静态检查：`ruff`、建议 `mypy`  
- 运行：`cd backend && ruff check app/ tests/ && pytest tests/unit/ -v`  
- 新 API 请补充 schema 字段说明，便于 OpenAPI  

### 前端（`frontend/`）

- TypeScript 严格模式；UI 使用 Ant Design  
- HTTP 调用优先 `src/api/`（`services/` 仅为兼容层）  
- 运行：`cd frontend && npm test && npm run build`  

## Pull Request 检查清单

- [ ] 已在本地跑通相关路径（Eager 或 Docker）  
- [ ] 新增/修改附带测试或说明为何无需测试  
- [ ] 未提交 `.env`、密钥、本地数据库文件  
- [ ] 文档（README / docs）已同步更新（若影响使用方式）  
- [ ] CI 通过  

## Issue

- Bug：请说明环境（OS、Python/Node 版本、Eager 还是 Docker）、复现步骤、期望与实际行为  
- 功能建议：说明场景与价值，避免仅一句话需求  

请使用仓库提供的 Issue 模板。

## 许可证

贡献代码默认同意以项目 [MIT License](LICENSE) 授权。

# 安全政策

## 支持的版本

| 版本 | 支持状态 |
|------|----------|
| 0.1.x / main | 安全修复会优先合入 `main` |
| 更早提交 | 尽力而为，不保证回溯补丁 |

## 报告漏洞

请**不要**通过公开 GitHub Issue 报告可被利用的安全漏洞。

建议通过以下方式私下联系维护者：

1. GitHub 仓库 **Security → Report a vulnerability**（若已启用）  
2. 或通过仓库 Owner 的 GitHub 私信说明问题概要与复现条件  

请包含：影响范围、复现步骤、是否已有利用、你的联系方式。我们会尽快确认并协商披露时间。

## 安全使用建议

- **切勿**将 `OPENAI_API_KEY`、`SECRET_KEY`、数据库密码提交到 Git  
- 生产环境建议：`AUTH_ENABLED=true` 并配置强随机 `API_KEYS`  
- 生产使用 PostgreSQL + `CELERY_TASK_ALWAYS_EAGER=false` + 网络隔离 Redis  
- 限制 `CORS_ORIGINS` 为真实前端域名  
- 定期升级依赖（`pip` / `npm audit`）  

## 密钥泄露时

1. 立即在服务商控制台轮换 API Key  
2. 轮换 `SECRET_KEY` 与数据库密码  
3. 检查 Git 历史是否误提交密钥，必要时使用历史清理工具并视为已泄露  

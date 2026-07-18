# AgentFlow-Eval 部署运维手册

> **部署边界（请先读）**  
> - **不强制在线部署**：本地 Eager 或 Docker 即可用于开发、演示与软著录屏。  
> - **Vercel 只能部署前端静态资源**，不能运行本项目的 Docker 全栈（FastAPI / Celery / Redis / Postgres）。  
> - 后端请使用：本机 Docker、云主机 `scripts/deploy-server.sh`、或 Railway 等容器平台。  
> - 前端若放在 Vercel，构建环境变量设置 `VITE_API_BASE_URL=https://你的API域名/api/v1`，并配置后端 `CORS_ORIGINS`。

## 目录

0. [本地与 Docker 快速部署](#0-本地与-docker-快速部署)
1. [GitHub Secrets 配置](#1-github-secrets-配置)
2. [生产服务器环境准备](#2-生产服务器环境准备)
3. [首次手动部署](#3-首次手动部署)
4. [通过 GitHub Actions 自动部署](#4-通过-github-actions-自动部署)
5. [回滚流程](#5-回滚流程)
6. [监控与维护](#6-监控与维护)
7. [常见问题](#7-常见问题)

---

## 0. 本地与 Docker 快速部署

详见仓库根目录 [README.md](../README.md)「快速开始」、[DEMO.md](./DEMO.md)、[production-checklist.md](./production-checklist.md)。

| 场景 | 命令入口 |
|------|----------|
| Windows 生成本地 env | `scripts/generate-deploy-env.ps1` |
| Windows Docker 一键（**含 migrate head + seed**） | `scripts/docker-up.ps1` |
| Compose | `cd backend && docker compose --env-file .env.docker up -d --build` |
| 迁移 only | `docker compose --env-file .env.docker run --rm migrate` |
| 部署后校验 | `scripts/post-deploy-verify.ps1` |
| 演示剧本 | `scripts/demo-playbook.ps1` |
| 生产配置检查 | `cd backend && make check-prod` |
| 云主机一键 | `scripts/setup-server.sh` + `scripts/deploy-server.sh` |
| Vercel 前端 + 自备 API | [vercel-postgres-self-api.md](./vercel-postgres-self-api.md) |

### 健康探针（K8s / Compose）

| 探针 | URL | 期望 |
|------|-----|------|
| Liveness | `/health/live` | 200 `alive` |
| Readiness | `/health/ready` | 200 `ready` |
| 兼容 | `/health` | healthy / degraded |

Compose `backend` 服务 healthcheck 使用 **`/health/ready`**。迁移服务 `migrate` 执行 `alembic upgrade head`（含 010 计费、011 慢任务）。

---

## 1. GitHub Secrets 配置

在 GitHub 仓库 `Settings` -> `Secrets and variables` -> `Actions` 中添加以下 Secrets：

| Secret | 用途 | 示例值 |
|--------|------|--------|
| `SSH_PRIVATE_KEY` | 部署服务器 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_HOST` | 部署服务器 IP/域名 | `192.168.1.100` or `app.example.com` |
| `DEPLOY_USER` | 部署服务器用户名 | `ubuntu` or `deploy` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | `sk-proj-xxxxx` |
| `SECRET_KEY` | FastAPI 应用密钥 | 随机 32 位字符串 |
| `CORS_ORIGINS` | 允许的 CORS 域名 | `https://app.example.com` |
| `DB_PASSWORD` | PostgreSQL 密码 | 强密码 |
| `FLOWER_USER` | Flower 监控用户名 | `admin` |
| `FLOWER_PASSWORD` | Flower 监控密码 | 强密码 |
| `WEBHOOK_URL` | 部署通知 Webhook (可选) | `https://hooks.slack.com/...` |
| `SONAR_TOKEN` | SonarQube 扫描 (可选) | `sqp_xxxxx` |
| `CODECOV_TOKEN` | Codecov 上传 (可选) | `xxxxx-xxxxx` |

### 1.1 生成 SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# 输出示例: abc123def456ghi789jkl012mno345pqr678stu901vwx
```

### 1.2 配置 SSH 部署密钥

```bash
# 1. 在部署服务器上创建部署用户
sudo adduser deploy
sudo usermod -aG docker deploy

# 2. 在本地生成 SSH 密钥对
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key

# 3. 将公钥复制到服务器
ssh-copy-id -i ~/.ssh/deploy_key.pub deploy@$DEPLOY_HOST

# 4. 查看私钥内容（复制到 GitHub Secrets）
cat ~/.ssh/deploy_key
```

### 1.3 生成 DB_PASSWORD

```bash
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## 2. 生产服务器环境准备

### 2.1 服务器初始化

```bash
# 连接到服务器
ssh deploy@$DEPLOY_HOST

# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose-plugin -y

# 安装 Git
sudo apt install git -y

# 创建应用目录
mkdir -p /app/agentflow-eval
cd /app/agentflow-eval

# 验证安装
docker --version
docker compose version
```

### 2.2 创建生产环境 .env 文件

在 `/app/agentflow-eval/.env` 中创建：

```bash
# 数据库
DB_USER=agentflow
DB_PASSWORD=<从 GitHub Secrets 获取>
DB_NAME=agentflow_prod

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=<从 GitHub Secrets 获取>

# FastAPI
ENV=prod
SECRET_KEY=<从 GitHub Secrets 获取>
CORS_ORIGINS=<从 GitHub Secrets 获取>

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Flower 监控
FLOWER_USER=admin
FLOWER_PASSWORD=<从 GitHub Secrets 获取>
```

### 2.3 配置 Nginx 反向代理 (可选)

```bash
# 安装 Nginx
sudo apt install nginx -y

# 创建站点配置
sudo tee /etc/nginx/sites-available/agentflow > /dev/null << 'NGINX'
server {
    listen 80;
    server_name app.example.com;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Flower Monitoring
    location /flower/ {
        proxy_pass http://localhost:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

# 启用站点
sudo ln -sf /etc/nginx/sites-available/agentflow /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 配置 HTTPS (Let's Encrypt)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d app.example.com
```

---

## 3. 首次手动部署

### 3.0 推荐：源码 + Docker Compose 一键部署（无需 GHCR）

适用于首次上云 / 单机 VPS。在服务器上执行：

```bash
# 1) 安装 Docker（Ubuntu/Debian，需 root）
curl -fsSL https://raw.githubusercontent.com/441732218-art/AgentFlow-Eval/main/scripts/setup-server.sh | sudo bash

# 2) 重新登录后，一键部署（替换密钥与公网 IP）
git clone https://github.com/441732218-art/AgentFlow-Eval.git /opt/agentflow-eval
cd /opt/agentflow-eval
OPENAI_API_KEY=sk-your-key PUBLIC_HOST=你的公网IP bash scripts/deploy-server.sh
```

部署成功后访问：

| 服务 | 地址 |
|------|------|
| 前端 | `http://你的公网IP/` （端口 80） |
| API 文档 | `http://你的公网IP:8000/docs` |
| Flower | `http://你的公网IP:5555` |

更新版本：

```bash
cd /opt/agentflow-eval
bash scripts/deploy-server.sh
```

> 云厂商安全组需放行 **80 / 8000**（可选 5555）。

### 3.1 使用预构建镜像部署（CI → GHCR）

```bash
cd /app/agentflow-eval

# 克隆代码（首次部署）
git clone https://github.com/441732218-art/AgentFlow-Eval.git .

# 拉取 Docker 镜像
export REGISTRY=ghcr.io
export IMAGE_TAG=latest
export GITHUB_REPOSITORY=441732218-art/AgentFlow-Eval

docker compose -f backend/docker-compose.prod.yml down
docker compose -f backend/docker-compose.prod.yml pull
docker compose -f backend/docker-compose.prod.yml up -d

# 运行数据库迁移
sleep 10
docker compose -f backend/docker-compose.prod.yml exec -T backend alembic upgrade head

# 种子数据（可选）
docker compose -f backend/docker-compose.prod.yml exec -T backend python -m app.core.seed

# 健康检查
curl -f http://localhost:8000/health
```

### 3.2 验证部署

```bash
# 检查所有容器运行状态
docker compose -f backend/docker-compose.prod.yml ps

# 查看日志
docker compose -f backend/docker-compose.prod.yml logs -f --tail=50 backend

# 访问服务
# Frontend:  http://app.example.com
# API Docs:  http://app.example.com/docs
# Flower:    http://app.example.com/flower/
```

---

## 4. 通过 GitHub Actions 自动部署

### 4.1 触发方式

| 方式 | 操作 | 适用场景 |
|------|------|---------|
| 手动触发 | GitHub Actions → deploy.yml → Run workflow | 日常更新 |
| Release 触发 | 创建新 Release → 自动触发 | 版本发布 |

### 4.2 部署流程

```
1. GitHub Actions 触发（手动或 Release）
2. 登录 ghcr.io（GitHub Container Registry）
3. SSH 连接到生产服务器
4. 拉取最新 Docker 镜像
5. docker-compose down（停止旧容器）
6. docker-compose up -d（启动新容器）
7. 等待服务就绪（sleep 10）
8. 运行数据库迁移（alembic upgrade head）
9. 健康检查验证（curl /health）
10. 清理旧镜像（docker image prune）
11. 发送 Webhook 通知
```

### 4.3 部署工作流文件

工作流定义在 `.github/workflows/deploy.yml`，支持：

- **环境选择**: `prod` / `staging`
- **自动迁移**: `alembic upgrade head`
- **健康检查**: `curl -f http://localhost:8000/health`
- **失败通知**: Webhook 通知

---

## 5. 回滚流程

### 5.1 快速回滚（服务器直接操作）

```bash
cd /app/agentflow-eval

# 查看可用镜像版本
docker image ls | grep agentflow

# 回滚到指定版本
export IMAGE_TAG=v1.0.0  # 或使用 commit SHA

# 修改 docker-compose.prod.yml 中的镜像标签
sed -i "s|IMAGE_TAG:.*|IMAGE_TAG: ${IMAGE_TAG}|g" backend/docker-compose.prod.yml

# 重新启动
docker compose -f backend/docker-compose.prod.yml down
docker compose -f backend/docker-compose.prod.yml up -d

# 验证
curl -f http://localhost:8000/health
```

### 5.2 通过 GitHub Actions 回滚

```bash
# 1. 创建指向旧版本的 tag
git tag -f v1.0.0-previous <commit-sha>
git push -f origin v1.0.0-previous

# 2. 在 GitHub 上创建 Release 指向该 tag
# 3. Release 触发 deploy.yml，自动部署旧版本
```

---

## 6. 监控与维护

### 6.1 日常检查命令

```bash
# 容器状态
docker compose -f backend/docker-compose.prod.yml ps

# 资源使用
docker stats --no-stream

# 日志查看
docker compose -f backend/docker-compose.prod.yml logs --tail=100 -f backend

# Celery 队列状态
docker compose -f backend/docker-compose.prod.yml exec -T celery-worker \
  celery -A app.core.celery_app.celery_app inspect active

# Flower 监控面板
# 浏览器访问 http://app.example.com/flower/
# 用户名: admin (默认)
# 密码:   <FLOWER_PASSWORD>
```

### 6.2 数据库备份

```bash
# 创建备份
docker compose -f backend/docker-compose.prod.yml exec -T postgres \
  pg_dump -U agentflow agentflow_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复备份
cat backup_20260101_120000.sql | docker compose -f backend/docker-compose.prod.yml exec -T postgres \
  psql -U agentflow agentflow_prod
```

### 6.3 日志轮转

```bash
# 创建 logrotate 配置
sudo tee /etc/logrotate.d/docker-containers > /dev/null << 'LOGROTATE'
/var/lib/docker/containers/*/*-json.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    maxsize 100M
}
LOGROTATE
```

---

## 7. 常见问题

### Q1: 部署后健康检查失败？

```bash
# 检查容器日志
docker compose -f backend/docker-compose.prod.yml logs --tail=50 backend

# 检查数据库连接
docker compose -f backend/docker-compose.prod.yml exec -T backend \
  python -c "
import asyncio
from sqlalchemy import text
from app.core.dependencies import async_session_factory

async def check():
    async with async_session_factory() as session:
        await session.execute(text('SELECT 1'))
        print('Database connection: OK')

asyncio.run(check())
"
```

### Q2: Celery 任务无法执行？

```bash
# 检查 Worker 状态
docker compose -f backend/docker-compose.prod.yml exec -T celery-worker \
  celery -A app.core.celery_app.celery_app status

# 检查 Redis 连接
docker compose -f backend/docker-compose.prod.yml exec -T redis redis-cli ping
# 应返回: PONG

# 查看 Worker 日志
docker compose -f backend/docker-compose.prod.yml logs --tail=50 celery-worker
```

### Q3: 前端无法连接到后端 API？

```bash
# 检查 CORS 配置
docker compose -f backend/docker-compose.prod.yml exec -T backend \
  python -c "from app.config import settings; print(settings.CORS_ORIGINS)"

# 检查 Nginx 配置
sudo nginx -t
sudo systemctl status nginx

# 测试 API 直连
curl -f http://localhost:8000/health
```

### Q4: 数据库迁移失败？

```bash
# 查看迁移历史
docker compose -f backend/docker-compose.prod.yml exec -T backend \
  alembic history

# 回滚一步
docker compose -f backend/docker-compose.prod.yml exec -T backend \
  alembic downgrade -1

# 重新升级
docker compose -f backend/docker-compose.prod.yml exec -T backend \
  alembic upgrade head
```

### Q5: 如何查看应用日志？

```bash
# 后端 API 日志
docker compose -f backend/docker-compose.prod.yml logs -f backend

# Celery Worker 日志
docker compose -f backend/docker-compose.prod.yml logs -f celery-worker

# Nginx 访问日志
sudo tail -f /var/log/nginx/access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/error.log
```

---

## 部署验证清单

- [ ] GitHub Secrets 全部配置完成
- [ ] 部署服务器已安装 Docker + Docker Compose
- [ ] SSH 密钥已配置并可连接
- [ ] 生产环境 `.env` 文件已创建
- [ ] Nginx + HTTPS 已配置
- [ ] `docker compose pull` 成功拉取镜像
- [ ] `docker compose up -d` 所有容器启动
- [ ] `alembic upgrade head` 迁移成功
- [ ] `/health` 端点返回 200
- [ ] 前端页面可正常访问
- [ ] GitHub Actions 部署工作流触发成功
- [ ] 回滚流程已验证可用

> 文档版本: 0.1.0 | 最后更新: 2026-07-08

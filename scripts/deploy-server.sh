#!/usr/bin/env bash
# AgentFlow-Eval — 在服务器上一键部署 / 更新
# 用法:
#   curl -fsSL ... | bash   # 或
#   bash scripts/deploy-server.sh
#   APP_DIR=/opt/agentflow-eval bash scripts/deploy-server.sh
#   OPENAI_API_KEY=sk-xxx bash scripts/deploy-server.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/441732218-art/AgentFlow-Eval.git}"
APP_DIR="${APP_DIR:-/opt/agentflow-eval}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="backend/docker-compose.yml"

echo "==> AgentFlow-Eval 部署"
echo "    APP_DIR=$APP_DIR"
echo "    BRANCH=$BRANCH"

# ---- 依赖检查 ----
need() { command -v "$1" >/dev/null 2>&1 || { echo "缺少依赖: $1"; exit 1; }; }
need git
need docker
docker compose version >/dev/null 2>&1 || { echo "需要 Docker Compose 插件 (docker compose)"; exit 1; }

# ---- 代码 ----
if [ ! -d "$APP_DIR/.git" ]; then
  echo "==> 首次克隆仓库"
  sudo mkdir -p "$(dirname "$APP_DIR")"
  if [ -w "$(dirname "$APP_DIR")" ] 2>/dev/null; then
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  else
    sudo git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
    sudo chown -R "$(id -u):$(id -g)" "$APP_DIR"
  fi
else
  echo "==> 拉取最新代码"
  cd "$APP_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi

cd "$APP_DIR"

# ---- 环境文件 ----
if [ ! -f backend/.env ]; then
  echo "==> 创建 backend/.env"
  if [ -f deploy.env.example ]; then
    cp deploy.env.example backend/.env
  else
    cp backend/.env.example backend/.env
  fi
  # 生成 SECRET_KEY
  if command -v python3 >/dev/null 2>&1; then
    SK=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  else
    SK=$(openssl rand -base64 48 | tr -d '\n/=+' | head -c 48)
  fi
  DB_PASS=$(openssl rand -base64 24 | tr -d '\n/=+' | head -c 24)
  FLOWER_PASS=$(openssl rand -base64 16 | tr -d '\n/=+' | head -c 16)

  # 粗略替换占位符（Linux sed）
  sed -i "s|SECRET_KEY=.*|SECRET_KEY=${SK}|" backend/.env
  sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${DB_PASS}|" backend/.env
  sed -i "s|请替换为强密码|${DB_PASS}|g" backend/.env
  sed -i "s|请替换为随机长字符串|${SK}|g" backend/.env
  sed -i "s|FLOWER_PASSWORD=.*|FLOWER_PASSWORD=${FLOWER_PASS}|" backend/.env || true
  sed -i "s|CELERY_TASK_ALWAYS_EAGER=.*|CELERY_TASK_ALWAYS_EAGER=false|" backend/.env
  sed -i "s|ENV=dev|ENV=prod|" backend/.env
  sed -i "s|DEBUG=true|DEBUG=false|" backend/.env
  # 同步 DATABASE_URL 密码
  sed -i "s|postgresql+asyncpg://agentflow:[^@]*@|postgresql+asyncpg://agentflow:${DB_PASS}@|" backend/.env

  if [ -n "${OPENAI_API_KEY:-}" ]; then
    sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY}|" backend/.env
  else
    echo "!! 警告: 未设置 OPENAI_API_KEY，评测功能不可用。请编辑 backend/.env"
  fi

  # 若提供了公网 IP / 域名，写入 CORS
  if [ -n "${PUBLIC_HOST:-}" ]; then
    sed -i "s|YOUR_SERVER_IP|${PUBLIC_HOST}|g" backend/.env
    sed -i "s|YOUR_DOMAIN|${PUBLIC_HOST}|g" backend/.env
  fi

  echo "==> 已生成 backend/.env（请妥善保管，不要提交到 Git）"
else
  echo "==> 已存在 backend/.env，跳过生成"
  if [ -n "${OPENAI_API_KEY:-}" ]; then
    sed -i "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_API_KEY}|" backend/.env
  fi
fi

# ---- 构建并启动（compose 内 migrate 服务先 alembic upgrade head）----
echo "==> docker compose build & up (incl. migrate)"
cd "$APP_DIR"
docker compose -f "$COMPOSE_FILE" build
docker compose -f "$COMPOSE_FILE" up -d

echo "==> 等待服务就绪 (/health/ready)..."
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/health/ready >/dev/null 2>&1; then
    echo "    backend ready"
    break
  fi
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo "!! 后端就绪检查超时，查看日志:"
    docker compose -f "$COMPOSE_FILE" logs --tail=80 backend migrate
    exit 1
  fi
done

# 双保险：已有库升级
echo "==> 确认数据库迁移 (alembic upgrade head)"
docker compose -f "$COMPOSE_FILE" run --rm migrate || \
  docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head || {
  echo "!! alembic 迁移跳过/失败（见 logs migrate）"
}

echo "==> 写入演示种子（best-effort）"
docker compose -f "$COMPOSE_FILE" exec -T backend python -m app.core.seed || true

echo ""
echo "============================================"
echo " 部署完成"
echo " 前端:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):80"
echo " API:   http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000"
echo " Ready: curl -s http://127.0.0.1:8000/health/ready"
echo " Me:    curl -s http://127.0.0.1:8000/api/v1/me"
echo " Docs:  http://$(hostname -I 2>/dev/null | awk '{print $1}'):8000/docs"
echo " Flower:http://$(hostname -I 2>/dev/null | awk '{print $1}'):5555  (admin / 见 backend/.env)"
echo " 校验:  见 docs/production-checklist.md"
echo " 日志:  docker compose -f backend/docker-compose.yml logs -f"
echo "============================================"

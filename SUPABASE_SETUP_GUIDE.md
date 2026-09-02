# AgentFlow-Eval 数据库迁移 — Supabase CLI 操作指南

> 当前项目：AgentFlow-Eval，数据库：PostgreSQL (agentflow_eval)
> 现有连接：`postgresql+asyncpg://agentflow@postgres:5432/agentflow_eval`

---

## 一、安装 Supabase CLI

推荐用 Scoop（Windows 上最稳的方式）：
```powershell
# 先装 Scoop（如果没有）
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# 安装 Supabase CLI
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

或者直接下载 exe：
```powershell
# 下载到项目根目录
Invoke-WebRequest -Uri "https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.exe" -OutFile "D:\AgentFlow-Eval\supabase.exe"
```

---

## 二、初始化本地项目

```bash
cd D:\AgentFlow-Eval
supabase init
```

这会创建 `supabase/` 目录，结构如下：
```
supabase/
├── config.toml      # 本地 Supabase 配置
├── migrations/      # 你的 SQL 迁移文件
├── seed.sql         # 种子数据（可选）
└── ...
```

---

## 三、启动本地 Supabase（需要 Docker）

```bash
supabase start
```

启动后访问：
- **Studio 面板**：http://localhost:54323
- **API**：http://localhost:54321
- **Postgres**：localhost:54322

---

## 四、创建数据库迁移文件

### 4.1 导出当前表结构

先把现有 Python 模型对应的表结构导出为 SQL：

```bash
# 如果本地 Docker Postgres 在运行：
docker exec agentflow-postgres pg_dump -U agentflow -d agentflow_eval --schema-only --no-owner > schema_dump.sql
```

### 4.2 创建迁移文件

```bash
# 创建初始迁移
supabase migration new init_schema

# 编辑生成的文件：supabase/migrations/XXXXXXXXXX_init_schema.sql
# 把 schema_dump.sql 中的 CREATE TABLE 语句粘贴进去
```

### 4.3 AgentFlow-Eval 核心表结构参考

```sql
-- 任务表
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    agent_config JSONB NOT NULL DEFAULT '{}',
    celery_task_id VARCHAR(255),
    is_archived BOOLEAN NOT NULL DEFAULT false,
    created_by VARCHAR(100) NOT NULL DEFAULT 'anonymous',
    tenant_id VARCHAR(36),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 测试用例表
CREATE TABLE test_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    input_data JSONB NOT NULL DEFAULT '{}',
    expected_output TEXT DEFAULT '',
    expected_tools TEXT[] DEFAULT '{}',
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 执行轨迹表
CREATE TABLE traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    test_suite_id UUID REFERENCES test_suites(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    steps JSONB DEFAULT '[]',
    final_answer TEXT DEFAULT '',
    total_tokens INTEGER DEFAULT 0,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost FLOAT NOT NULL DEFAULT 0,
    agent_version VARCHAR(100),
    prompt_version VARCHAR(100),
    model_version VARCHAR(100),
    tool_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 指标评分表
CREATE TABLE metric_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trace_id UUID NOT NULL REFERENCES traces(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    score FLOAT NOT NULL DEFAULT 0,
    confidence FLOAT,
    is_human_reviewed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AB 实验表
CREATE TABLE ab_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    alpha FLOAT DEFAULT 0.05,
    min_sample_size INTEGER DEFAULT 100,
    primary_metric VARCHAR(100) DEFAULT 'conversion',
    control_variant_key VARCHAR(100),
    source_experiment_id UUID,
    config JSONB DEFAULT '{}',
    created_by VARCHAR(100) NOT NULL DEFAULT 'anonymous',
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 索引
CREATE INDEX ix_tasks_owner_archived_created ON tasks(created_by, is_archived, created_at DESC);
CREATE INDEX ix_tasks_status_created ON tasks(status, created_at DESC);
CREATE INDEX ix_tasks_created_by ON tasks(created_by);
CREATE INDEX ix_traces_task_id ON traces(task_id);
CREATE INDEX ix_metric_scores_trace_id ON metric_scores(trace_id);
```

### 4.4 应用到本地数据库测试

```bash
supabase db reset
```

---

## 五、连接线上 Neon/Supabase 项目

### 如果用的是 Supabase 云端：

```bash
# 1. 登录
supabase login

# 2. 关联项目（从 Supabase Dashboard → Settings → General 找 Project Ref）
supabase link --project-ref xxxxxxxxxxxxxxxxxx

# 3. 推送迁移到线上
supabase db push
```

### 如果用的是 Neon（你提到的"霓虹灯数据库"）：

Neon 直接用 Postgres 连接字符串即可，不需要 Supabase CLI：

```bash
# 1. 在 Neon Dashboard 创建数据库，复制连接字符串
# 格式：postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/dbname?sslmode=require

# 2. 用 psql 或 DBeaver 连接 Neon，执行迁移
psql "postgresql://user:password@ep-xxxx.us-east-2.aws.neon.tech/dbname?sslmode=require" -f supabase/migrations/XXXXXXXXXX_init_schema.sql

# 3. 修改 backend/.env.docker 中的 DATABASE_URL
# DATABASE_URL=postgresql+asyncpg://user:password@ep-xxxx.us-east-2.aws.neon.tech/dbname?sslmode=require
```

---

## 六、验证连接

```bash
# 启动后端
cd D:\AgentFlow-Eval\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 测试健康检查
curl http://127.0.0.1:8000/health/ready
```

---

## ⚠️ 重要提示

1. **不要用 `supabase db push` 推送到 Neon**——Supabase CLI 是专门给 Supabase 平台用的
2. Neon 是标准的 Postgres，用任何 Postgres 客户端都能连接
3. 你的项目用的是 **SQLAlchemy + Alembic**，也可以用 `alembic` 管理迁移（更 Pythonic）

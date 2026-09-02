# (c) 2026 AgentFlow-Eval | Author: 李凯昕
import os, subprocess, sys
from pathlib import Path
env = os.environ.copy()
p = Path("backend/.env.docker") if Path("backend/.env.docker").exists() else Path(".env.docker")
for line in p.read_text(encoding="utf-8").splitlines():
line=line.strip()
if not line or line.startswith("#") or "=" not in line: continue
k,v=line.split("=",1)
env[k.strip()]=v.strip()
pu=env.get("POSTGRES_USER","agentflow")
pp=env.get("POSTGRES_PASSWORD","")
pd=env.get("POSTGRES_DB","agentflow_eval")
env["DATABASE_URL"]=f"postgresql+asyncpg://{pu}:{pp}@127.0.0.1:5432/{pd}"
env["REDIS_URL"]="redis://127.0.0.1:6379/0"
env["CELERY_BROKER_URL"]=env["REDIS_URL"]
env["CELERY_RESULT_BACKEND"]=env["REDIS_URL"]
env["CELERY_TASK_ALWAYS_EAGER"]="true"
env["TASK_QUEUE_BACKEND"]="eager"
env["DEPLOY_PROFILE"]="lite"
env["ENV"]="dev"
env["DEBUG"]="true"
env["AUTH_ENABLED"]="false"
env["BILLING_ENABLED"]="false"
env["LOG_DB_SINK"]="true"
env["PYTHONPATH"]=str(Path(".").resolve())
os.chdir(str(Path(".").resolve()))
log=open("uvicorn_docker_db.log","w",encoding="utf-8")
proc=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000"], env=env, stdout=log, stderr=log)
print(proc.pid)

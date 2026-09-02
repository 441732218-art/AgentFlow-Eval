import os, sys
os.chdir(r"D:\AgentFlow-Eval\backend")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/agentflow_lite.db"
os.environ["AUTH_ENABLED"] = "false"
os.environ["BILLING_ENABLED"] = "false"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["TASK_QUEUE_BACKEND"] = "eager"
os.environ["DEPLOY_PROFILE"] = "lite"
os.environ["ENV"] = "dev"
sys.path.insert(0, r"D:\AgentFlow-Eval\backend")
os.makedirs("data", exist_ok=True)

print("Starting...")
import uvicorn
uvicorn.run("app.main:app", host="127.0.0.1", port=9000, reload=False, log_level="info")

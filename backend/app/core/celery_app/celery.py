# (c) 2026 AgentFlow-Eval
"""Celery 应用配置 —— 初始化 Celery 实例并加载任务模块。"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "agentflow_eval",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# 加载任务模块
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# 自动发现任务
celery_app.autodiscover_tasks(["app.core.celery_app"])

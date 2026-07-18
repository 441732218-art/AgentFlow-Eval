# (c) 2026 AgentFlow-Eval
# Single-stage backend image (lighter for Docker Desktop)

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Prefer docker-slim requirements when present
COPY requirements.docker.txt requirements.txt ./
RUN pip install --no-cache-dir -r requirements.docker.txt

COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/

RUN mkdir -p logs

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

EXPOSE 8000

# 2 workers is enough for local / small VPS; override via compose if needed
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

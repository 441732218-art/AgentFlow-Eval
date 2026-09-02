# (c) 2026 AgentFlow-Eval | Author: 李凯昕
"""API functional smoke against local backend + Docker Postgres."""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
BASE = "http://127.0.0.1:8000"
API = BASE + "/api/v1"
results: list[dict] = []
def req(name: str, method: str, path: str, body=None) -> tuple[int, str]:
if path.startswith("http"):
url = path
elif path.startswith("/health") or path.startswith("/metrics"):
url = BASE + path
else:
url = API + path
data = None
headers: dict[str, str] = {}
if body is not None:
data = json.dumps(body).encode("utf-8")
headers["Content-Type"] = "application/json"
request = urllib.request.Request(url, data=data, headers=headers, method=method)
try:
with urllib.request.urlopen(request, timeout=90) as resp:
code = resp.status
text = resp.read().decode("utf-8", errors="replace")
ok = 200 <= code < 300
results.append({"name": name, "code": code, "ok": ok, "detail": text[:200]})
return code, text
except urllib.error.HTTPError as e:
text = e.read().decode("utf-8", errors="replace")
results.append({"name": name, "code": e.code, "ok": False, "detail": text[:200]})
return e.code, text
except Exception as e: # noqa: BLE001
results.append({"name": name, "code": 0, "ok": False, "detail": str(e)[:200]})
return 0, str(e)
def main() -> None:
for _ in range(30):
code, _ = req("probe", "GET", "/health/ready")
if code == 200:
results.clear()
break
time.sleep(0.5)
checks = [
("health", "GET", "/health"),
("health_live", "GET", "/health/live"),
("health_ready", "GET", "/health/ready"),
("metrics", "GET", "/metrics"),
("me", "GET", "/me"),
("dashboard", "GET", "/dashboard?days=7"),
("dashboard_stats", "GET", "/dashboard/stats"),
("tasks_list", "GET", "/tasks?page=1&page_size=10"),
("tools", "GET", "/tools"),
("settings", "GET", "/settings"),
("audit", "GET", "/audit?page=1&page_size=5"),
("traces", "GET", "/traces?page=1&page_size=5"),
("logs", "GET", "/logs?page=1&page_size=10"),
("logs_stats", "GET", "/logs/statistics?days=7"),
("obs_kpis", "GET", "/observability/kpis?days=7"),
("obs_slow", "GET", "/observability/slow-tasks?limit=10"),
("obs_topo", "GET", "/observability/error-topology?days=7"),
("diagnosis_list", "GET", "/diagnosis?limit=10"),
("plugins", "GET", "/plugins"),
("billing_plans", "GET", "/billing/plans"),
("billing_quota", "GET", "/billing/quota"),
("ab_list", "GET", "/ab"), # list is GET /ab (not /ab/experiments)
("experiments", "GET", "/experiments"),
("media_list", "GET", "/media"),
]
for name, method, path in checks:
req(name, method, path)
code, text = req(
"task_create",
"POST",
"/tasks",
{
"name": "容器栈联调任务",
"description": "Docker Postgres + Celery",
"agent_config": {
"model": "gpt-4o-mini",
"temperature": 0,
"max_iterations": 3,
},
},
)
tid = None
try:
tid = json.loads(text).get("id")
except Exception:
tid = None
if tid:
req(
"task_suites",
"POST",
f"/tasks/{tid}/test-suites",
[
{
"user_query": "1+1等于几？",
"expected_output": "2",
"expected_tools": [],
}
],
)
req("task_get", "GET", f"/tasks/{tid}")
req("task_execute", "POST", f"/tasks/{tid}/execute", {})
for i in range(12):
time.sleep(5)
c, t = req(f"task_poll_{i}", "GET", f"/tasks/{tid}")
try:
st = json.loads(t).get("status")
except Exception:
st = None
if st in {"completed", "failed", "cancelled", "timeout"}:
break
req("task_report", "GET", f"/reports/{tid}")
req("diagnosis_task", "GET", f"/diagnosis/{tid}")
_, text = req("tasks_for_demo", "GET", "/tasks?page=1&page_size=20")
try:
items = json.loads(text).get("items") or []
demo = next((t for t in items if "Demo" in (t.get("name") or "")), None)
if demo:
req("diagnosis_demo", "GET", f"/diagnosis/{demo['id']}")
except Exception:
pass
_, text = req("traces_sample", "GET", "/traces?page=1&page_size=1")
try:
items = json.loads(text).get("items") or []
if items:
req("trace_detail", "GET", f"/traces/{items[0]['id']}")
except Exception:
pass
final = [r for r in results if r["name"] not in {"probe", "tasks_for_demo", "traces_sample"}]
pass_n = sum(1 for r in final if r["ok"])
fail_n = sum(1 for r in final if not r["ok"])
print(f"PASS={pass_n} FAIL={fail_n} TOTAL={len(final)}")
for r in final:
flag = "OK" if r["ok"] else "FAIL"
print(f"{flag:4} {r['code']:3} {r['name']:18} {r['detail'][:90]}")
out = Path(__file__).resolve().parents[1] / "docs" / "_docker_api_test_results.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
json.dumps({"pass": pass_n, "fail": fail_n, "results": final}, ensure_ascii=False, indent=2),
encoding="utf-8",
)
print("wrote", out)
if __name__ == "__main__":
main()

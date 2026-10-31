# (c) 2026 AgentFlow-Eval
"""E9/E11 isolated contract tests for POST .../test-suites/import-csv.

Uses ASGI + dependency-overridden temporary SQLite only.
Does NOT use settings.DATABASE_URL (default agentflow_eval.db).
Does NOT cover /test-suites/upload.

Schema setup uses CreateTable/DropTable (no CREATE INDEX) so duplicate
index names on production models do not break SQLite init, and global
Base.metadata.indexes are left unmodified.

E15h-1: UUID temp SQLite; owned-file unlink only; deps.engine /
async_session_factory rebound; reversible get_db override (no clear());
LOG_DB_SINK=False; AOLS queue snapshot/restore.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.schema import CreateTable, DropTable

from app.config import settings
from app.core import dependencies as deps
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base
from app.models.test_suite import TestSuite

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
IMPORT_PATH = "/api/v1/tasks/{tid}/test-suites/import-csv"


def _create_tables_without_indexes(connection) -> None:
    """Create tables only — avoids duplicate-index create_all failures."""
    for table in Base.metadata.sorted_tables:
        connection.execute(CreateTable(table))


def _drop_tables(connection) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(DropTable(table, if_exists=True))


@pytest_asyncio.fixture
async def api_env():
    """Yield ASGI client + session factory bound to a unique temp SQLite file."""
    from app.core.observability.aols.sinks import db as aols_db_sink

    db_path = _BACKEND_ROOT / f"test_import_csv_e9_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name.startswith("test_import_csv_e9_")
    # Guard: fixture must not mutate global index collections
    index_fingerprint_before = {
        t.name: sorted(i.name or "" for i in t.indexes)
        for t in Base.metadata.tables.values()
    }

    owned = not db_path.exists()

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(_create_tables_without_indexes)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    had_get_db = get_db in app.dependency_overrides
    prev_get_db = app.dependency_overrides.get(get_db)
    prev_engine = deps.engine
    prev_factory = deps.async_session_factory
    prev_db_url = settings.DATABASE_URL
    prev_sink = bool(getattr(settings, "LOG_DB_SINK", True))

    with aols_db_sink._lock:
        prev_queue = list(aols_db_sink._queue)
        aols_db_sink._queue.clear()

    deps.engine = engine
    deps.async_session_factory = factory
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:

            class Env:
                def __init__(self) -> None:
                    self.client = client
                    self.factory = factory

                async def suite_count(self, task_id: str) -> int:
                    async with factory() as session:
                        result = await session.execute(
                            select(TestSuite).where(TestSuite.task_id == task_id)
                        )
                        return len(result.scalars().all())

                async def suites(self, task_id: str) -> list[TestSuite]:
                    async with factory() as session:
                        result = await session.execute(
                            select(TestSuite).where(TestSuite.task_id == task_id)
                        )
                        rows = list(result.scalars().all())
                        # Detach field snapshots before session closes
                        return [
                            type(
                                "SuiteSnap",
                                (),
                                {
                                    "user_query": s.user_query,
                                    "expected_output": s.expected_output,
                                    "expected_tools": list(s.expected_tools or []),
                                },
                            )()
                            for s in rows
                        ]

            yield Env()
    finally:
        # Drain this fixture's AOLS items while sink still off / URL still UUID
        with aols_db_sink._lock:
            aols_db_sink._queue.clear()
            aols_db_sink._queue.extend(prev_queue)

        if had_get_db:
            app.dependency_overrides[get_db] = prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)

        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory

        async with engine.begin() as conn:
            await conn.run_sync(_drop_tables)
        await engine.dispose()
        if owned and db_path.exists():
            try:
                db_path.unlink()
            except OSError:
                pass
        index_fingerprint_after = {
            t.name: sorted(i.name or "" for i in t.indexes)
            for t in Base.metadata.tables.values()
        }
        assert index_fingerprint_before == index_fingerprint_after, (
            "Fixture must not mutate Base.metadata indexes"
        )


@pytest.fixture
def api_client(api_env):
    """Backward-compatible client accessor for older test names."""
    return api_env.client


async def _create_task(client: AsyncClient, name: str = "e9-import-csv") -> str:
    r = await client.post(
        "/api/v1/tasks",
        json={"name": name, "description": "e9", "agent_config": {}},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _csv_file(name: str, body: bytes | str, content_type: str = "text/csv"):
    raw = body.encode("utf-8") if isinstance(body, str) else body
    return {"file": (name, raw, content_type)}


@pytest.mark.asyncio
async def test_import_csv_valid_creates_suites(api_env):
    tid = await _create_task(api_env.client)
    csv_body = (
        "query,expected_output,expected_tools\n"
        "q1,a1,calculator\n"
        "q2,a2,web_search\n"
    )
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("cases.csv", csv_body),
    )
    assert u.status_code == 201, u.text
    body = u.json()
    assert body["task_id"] == tid
    assert body["created"] == 2
    assert body["skipped"] == 0
    assert body.get("filename") == "cases.csv"
    assert body["message"] == "Imported 2 test suite(s) from CSV"

    detail = await api_env.client.get(f"/api/v1/tasks/{tid}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["test_suite_count"] == 2

    suites = await api_env.suites(tid)
    assert len(suites) == 2
    by_q = {s.user_query: s for s in suites}
    assert by_q["q1"].expected_output == "a1"
    assert by_q["q1"].expected_tools == ["calculator"]
    assert by_q["q2"].expected_output == "a2"
    assert by_q["q2"].expected_tools == ["web_search"]


@pytest.mark.asyncio
async def test_import_csv_empty_query_rows_increment_skipped(api_env):
    tid = await _create_task(api_env.client, name="e9-skipped")
    csv_body = (
        "query,expected_output,expected_tools\n"
        "keep-me,out1,tool_a\n"
        ",blank-query,tool_b\n"
        "   ,whitespace-query,tool_c\n"
    )
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("mixed.csv", csv_body),
    )
    assert u.status_code == 201, u.text
    body = u.json()
    assert body["created"] == 1
    assert body["skipped"] == 2
    assert "1 test suite(s) from CSV" in body["message"]
    assert "2 row(s) skipped" in body["message"]

    assert await api_env.suite_count(tid) == 1
    suites = await api_env.suites(tid)
    assert suites[0].user_query == "keep-me"


@pytest.mark.asyncio
async def test_import_csv_empty_file_returns_400_without_writes(api_env):
    tid = await _create_task(api_env.client, name="e9-empty")
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("empty.csv", b""),
    )
    assert u.status_code == 400, u.text
    assert u.json()["detail"] == "Empty file"
    assert await api_env.suite_count(tid) == 0
    detail = await api_env.client.get(f"/api/v1/tasks/{tid}")
    assert detail.json()["test_suite_count"] == 0


@pytest.mark.asyncio
async def test_import_csv_wrong_extension_returns_400(api_env):
    tid = await _create_task(api_env.client, name="e9-ext")
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file(
            "cases.txt",
            "query,expected_output\nq1,a1\n",
            "text/plain",
        ),
    )
    assert u.status_code == 400, u.text
    assert u.json()["detail"] == "Only .csv files are accepted"
    assert await api_env.suite_count(tid) == 0


@pytest.mark.asyncio
async def test_import_csv_missing_query_column_returns_400_without_writes(api_env):
    tid = await _create_task(api_env.client, name="e9-cols")
    csv_body = "expected_output,expected_tools\na1,calculator\n"
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("nocol.csv", csv_body),
    )
    assert u.status_code == 400, u.text
    assert "query" in u.json()["detail"] and "user_query" in u.json()["detail"]
    assert await api_env.suite_count(tid) == 0


@pytest.mark.asyncio
async def test_import_csv_all_rows_invalid_returns_400_without_writes(api_env):
    tid = await _create_task(api_env.client, name="e9-all-skip")
    csv_body = "query,expected_output,expected_tools\n,,\n , , \n"
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("allbad.csv", csv_body),
    )
    assert u.status_code == 400, u.text
    detail = u.json()["detail"]
    assert "No valid rows found in CSV" in detail
    assert "skipped" in detail.lower()
    assert await api_env.suite_count(tid) == 0


@pytest.mark.asyncio
async def test_import_csv_unknown_task_returns_404(api_env):
    missing = "00000000-0000-0000-0000-000000000000"
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=missing),
        files=_csv_file("cases.csv", "query,expected_output\nq1,a1\n"),
    )
    assert u.status_code == 404, u.text


@pytest.mark.asyncio
async def test_import_csv_extra_columns_returns_400_not_500(api_env):
    """Ragged rows produce DictReader None keys — must be 400, never 500."""
    tid = await _create_task(api_env.client, name="e11-ragged")
    # More fields than headers → restkey None
    csv_body = "query,expected_output\nq1,a1,extra_col\n"
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("ragged.csv", csv_body),
    )
    assert u.status_code == 400, u.text
    assert u.status_code != 500
    assert "extra columns" in u.json()["detail"].lower() or "invalid" in u.json()["detail"].lower()
    assert await api_env.suite_count(tid) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "header,query_cell",
    [
        ("query", "from-query"),
        ("Query", "from-Query"),
        ("QUERY", "from-QUERY"),
        ("user_query", "from-user_query"),
    ],
)
async def test_import_csv_header_case_variants(api_env, header, query_cell):
    tid = await _create_task(api_env.client, name=f"e11-case-{header}")
    csv_body = f"{header},expected_output,expected_tools\n{query_cell},out1,tool_x\n"
    u = await api_env.client.post(
        IMPORT_PATH.format(tid=tid),
        files=_csv_file("case.csv", csv_body),
    )
    assert u.status_code == 201, u.text
    assert u.json()["created"] == 1
    assert u.json()["skipped"] == 0
    suites = await api_env.suites(tid)
    assert len(suites) == 1
    assert suites[0].user_query == query_cell
    assert suites[0].expected_output == "out1"
    assert suites[0].expected_tools == ["tool_x"]

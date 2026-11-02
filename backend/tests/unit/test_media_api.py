# (c) 2026 AgentFlow-Eval
"""API tests for multimodal media endpoints.

E15d-2: unique UUID temp SQLite; reversible get_db override; deps.engine /
async_session_factory rebound; AOLS LOG_DB_SINK disabled. No fixed
./test_media_api.db and no dependency_overrides.clear().
"""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core import dependencies as deps
from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


def _png() -> bytes:
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (4, 4), color=(10, 20, 200)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
            "de0000000c4944415408d763f8ffff3f0005fe02fea75b1c0000000049454e44ae426082"
        )


@pytest_asyncio.fixture
async def api_client(tmp_path, monkeypatch):
    from app.core.observability.aols.sinks import db as aols_db_sink

    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr("app.config.settings.STORAGE_BACKEND", "local")
    monkeypatch.setattr(
        "app.config.settings.LOCAL_STORAGE_PATH", str(tmp_path / "uploads")
    )
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)

    db_path = _BACKEND_ROOT / f"test_media_api_{uuid4().hex}.db"
    test_db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    assert settings.DATABASE_URL != test_db_url
    assert "agentflow_eval.db" not in test_db_url
    assert db_path.name != "test_media_api.db"

    if db_path.exists():
        db_path.unlink()

    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    deps.engine = engine
    deps.async_session_factory = factory
    settings.DATABASE_URL = test_db_url
    settings.LOG_DB_SINK = False
    app.dependency_overrides[get_db] = _override

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        if had_get_db:
            app.dependency_overrides[get_db] = prev_get_db
        else:
            app.dependency_overrides.pop(get_db, None)
        try:
            with aols_db_sink._lock:
                aols_db_sink._queue.clear()
        except Exception:
            pass
        settings.LOG_DB_SINK = prev_sink
        settings.DATABASE_URL = prev_db_url
        deps.engine = prev_engine
        deps.async_session_factory = prev_factory
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        try:
            if db_path.exists():
                db_path.unlink()
        except OSError:
            pass


@pytest.mark.asyncio
async def test_formats(api_client):
    r = await api_client.get("/api/v1/media/formats")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["extensions"]) >= 5
    assert ".pdf" in body["extensions"]
    assert ".png" in body["extensions"]
    assert ".xlsx" in body["extensions"]


@pytest.mark.asyncio
async def test_upload_text_and_evaluate(api_client):
    files = {
        "file": ("notes.txt", b"AgentFlow multimodal evaluation scores", "text/plain")
    }
    data = {"extract": "true"}
    r = await api_client.post("/api/v1/media/upload", files=files, data=data)
    assert r.status_code == 201, r.text
    asset = r.json()
    assert asset["media_kind"] == "text"
    assert "AgentFlow" in asset["extracted_text"]

    ev = await api_client.post(
        f"/api/v1/media/{asset['id']}/evaluate",
        json={
            "query": "scores",
            "expected_text": "evaluation scores",
            "use_vision_llm": False,
        },
    )
    assert ev.status_code == 200, ev.text
    body = ev.json()
    assert body["total"] >= 0
    assert "content_coverage" in body["scores"]


@pytest.mark.asyncio
async def test_upload_csv(api_client):
    csv_body = b"metric,value\naccuracy,0.9\nrecall,0.8\n"
    r = await api_client.post(
        "/api/v1/media/upload",
        files={"file": ("m.csv", csv_body, "text/csv")},
        data={"extract": "true"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["media_kind"] == "spreadsheet"


@pytest.mark.asyncio
async def test_upload_image(api_client):
    r = await api_client.post(
        "/api/v1/media/upload",
        files={"file": ("x.png", _png(), "image/png")},
        data={"extract": "true"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["media_kind"] == "image"
    assert body["features"] is not None


@pytest.mark.asyncio
async def test_reject_bad_extension(api_client):
    r = await api_client.post(
        "/api/v1/media/upload",
        files={"file": ("x.exe", b"MZ", "application/octet-stream")},
        data={"extract": "false"},
    )
    assert r.status_code in (400, 422)

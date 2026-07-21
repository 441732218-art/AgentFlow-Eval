# (c) 2026 AgentFlow-Eval
"""API tests for multimodal media endpoints."""

from __future__ import annotations

import io
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.dependencies import get_db
from app.main import app
from app.models.base import Base

TEST_DB = "sqlite+aiosqlite:///./test_media_api.db"


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
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setattr("app.config.settings.STORAGE_BACKEND", "local")
    monkeypatch.setattr(
        "app.config.settings.LOCAL_STORAGE_PATH", str(tmp_path / "uploads")
    )
    monkeypatch.setattr("app.config.settings.AUTH_ENABLED", False)
    monkeypatch.setattr("app.config.settings.RBAC_ENABLED", False)

    engine = create_async_engine(TEST_DB, echo=False)
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

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_media_api.db")
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

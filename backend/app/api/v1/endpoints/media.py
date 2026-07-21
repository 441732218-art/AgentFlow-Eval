# (c) 2026 AgentFlow-Eval
"""Multimodal media upload, extraction, and evaluation APIs."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db
from app.core.multimodal.evaluator import rule_multimodal_score, vision_llm_score
from app.core.multimodal.registry import (
    SUPPORTED_EXTENSIONS,
    detect_media_kind,
    extract_media,
)
from app.core.multimodal.storage import get_storage
from app.core.multimodal.types import MediaKind
from app.core.rbac import Permission, require_permission
from app.models.media_asset import MediaAsset
from app.schemas.media import (
    MediaAssetResponse,
    MediaExtractResponse,
    MultimodalEvalRequest,
    MultimodalEvalResponse,
    SupportedFormatsResponse,
)
from app.utils.exceptions import NotFoundError, ValidationError

router = APIRouter()


def _actor(request: Request) -> str:
    return getattr(request.state, "actor", None) or "anonymous"


def _asset_to_response(asset: MediaAsset) -> MediaAssetResponse:
    return MediaAssetResponse(
        id=asset.id,
        filename=asset.filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
        media_kind=asset.media_kind,
        storage_backend=asset.storage_backend,
        storage_key=asset.storage_key,
        extracted_text=(asset.extracted_text or "")[:50_000],
        features=asset.features,
        extract_meta=asset.extract_meta,
        task_id=asset.task_id,
        test_suite_id=asset.test_suite_id,
        created_by=asset.created_by,
        created_at=asset.created_at,
    )


@router.get("/formats", response_model=SupportedFormatsResponse)
@require_permission(Permission.TASK_READ)
async def list_supported_formats(request: Request) -> SupportedFormatsResponse:
    """List supported upload extensions and storage backend."""
    return SupportedFormatsResponse(
        extensions=sorted(SUPPORTED_EXTENSIONS),
        kinds=[k.value for k in MediaKind],
        max_upload_bytes=int(
            getattr(settings, "MEDIA_MAX_UPLOAD_BYTES", 20 * 1024 * 1024)
        ),
        storage_backend=str(getattr(settings, "STORAGE_BACKEND", "local")),
    )


@router.post("/upload", response_model=MediaAssetResponse, status_code=201)
@require_permission(Permission.TASK_CREATE)
async def upload_media(
    request: Request,
    file: UploadFile = File(..., description="Image, PDF, Excel/CSV, or text file"),
    task_id: str | None = Form(default=None),
    test_suite_id: str | None = Form(default=None),
    extract: bool = Form(default=True),
    session: AsyncSession = Depends(get_db),
) -> MediaAssetResponse:
    """Upload a multimodal file, store it, and optionally run extraction."""
    actor = _actor(request)
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext and ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext}'. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    raw = await file.read()
    max_bytes = int(getattr(settings, "MEDIA_MAX_UPLOAD_BYTES", 20 * 1024 * 1024))
    if len(raw) > max_bytes:
        raise ValidationError(f"File exceeds max size of {max_bytes} bytes")
    if not raw:
        raise ValidationError("Empty file")

    content_type = file.content_type or "application/octet-stream"
    kind = detect_media_kind(filename, content_type)
    sha = hashlib.sha256(raw).hexdigest()

    storage = get_storage()
    stored = await storage.put(
        raw,
        filename=filename,
        content_type=content_type,
        prefix=f"media/{actor}",
    )

    extracted_text = ""
    features: dict[str, Any] | None = None
    extract_meta: dict[str, Any] | None = None
    if extract:
        result = extract_media(raw, filename, content_type)
        extracted_text = result.text or ""
        features = result.features
        extract_meta = {
            "metadata": result.metadata,
            "pages": result.pages,
            "tables": result.tables,
            "warnings": result.warnings,
            "kind": result.kind.value,
        }

    asset = MediaAsset(
        filename=filename,
        content_type=content_type,
        size_bytes=len(raw),
        sha256=sha,
        media_kind=kind.value,
        storage_backend=stored.backend,
        storage_key=stored.key,
        extracted_text=extracted_text,
        features=features,
        extract_meta=extract_meta,
        task_id=task_id,
        test_suite_id=test_suite_id,
        created_by=actor,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return _asset_to_response(asset)


@router.get("/{asset_id}", response_model=MediaAssetResponse)
@require_permission(Permission.TASK_READ)
async def get_media(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MediaAssetResponse:
    asset = await _load_asset(session, asset_id)
    return _asset_to_response(asset)


@router.post("/{asset_id}/extract", response_model=MediaExtractResponse)
@require_permission(Permission.TASK_UPDATE)
async def reextract_media(
    asset_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MediaExtractResponse:
    """Re-run extraction on a stored asset."""
    asset = await _load_asset(session, asset_id)
    storage = get_storage()
    try:
        raw = await storage.get(asset.storage_key)
    except FileNotFoundError as exc:
        raise NotFoundError("Media blob", asset.storage_key) from exc

    result = extract_media(raw, asset.filename, asset.content_type)
    asset.extracted_text = result.text or ""
    asset.features = result.features
    asset.extract_meta = {
        "metadata": result.metadata,
        "pages": result.pages,
        "tables": result.tables,
        "warnings": result.warnings,
        "kind": result.kind.value,
    }
    asset.media_kind = result.kind.value
    await session.commit()

    return MediaExtractResponse(
        asset_id=asset.id,
        kind=result.kind.value,
        text=result.text,
        features=result.features,
        metadata=result.metadata,
        pages=result.pages,
        tables=result.tables,
        warnings=result.warnings,
    )


@router.post("/{asset_id}/evaluate", response_model=MultimodalEvalResponse)
@require_permission(Permission.EVALUATION_SUBMIT)
async def evaluate_media(
    asset_id: str,
    body: MultimodalEvalRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MultimodalEvalResponse:
    """Run multimodal evaluation (rule + optional vision LLM)."""
    asset = await _load_asset(session, asset_id)
    storage = get_storage()
    try:
        raw = await storage.get(asset.storage_key)
    except FileNotFoundError as exc:
        raise NotFoundError("Media blob", asset.storage_key) from exc

    # Prefer stored extraction; refresh if empty
    if not asset.extracted_text and not asset.features:
        extracted = extract_media(raw, asset.filename, asset.content_type)
        asset.extracted_text = extracted.text
        asset.features = extracted.features
        asset.extract_meta = {
            "metadata": extracted.metadata,
            "pages": extracted.pages,
            "tables": extracted.tables,
            "warnings": extracted.warnings,
            "kind": extracted.kind.value,
        }
        await session.commit()
    else:
        from app.core.multimodal.types import ExtractResult

        meta = asset.extract_meta or {}
        extracted = ExtractResult(
            kind=MediaKind(asset.media_kind)
            if asset.media_kind in {k.value for k in MediaKind}
            else MediaKind.OTHER,
            text=asset.extracted_text or "",
            features=asset.features or {},
            metadata=meta.get("metadata") or {},
            pages=meta.get("pages"),
            tables=meta.get("tables") or [],
            warnings=meta.get("warnings") or [],
        )

    if body.use_vision_llm and extracted.kind == MediaKind.IMAGE:
        score = await vision_llm_score(
            image_bytes=raw,
            extracted=extracted,
            query=body.query,
            expected_text=body.expected_text,
            model=body.model,
        )
    else:
        score = rule_multimodal_score(
            extracted,
            expected_text=body.expected_text,
            query=body.query,
        )
        if body.use_vision_llm and extracted.kind != MediaKind.IMAGE:
            # Text-heavy multimodal via vision model without image
            score = await vision_llm_score(
                image_bytes=None,
                extracted=extracted,
                query=body.query,
                expected_text=body.expected_text,
                model=body.model,
            )

    return MultimodalEvalResponse(
        asset_id=asset.id,
        mode=score.get("mode", "rule_multimodal"),
        scores=score.get("scores") or {},
        total=float(score.get("total") or 0),
        reason=str(score.get("reason") or ""),
        kind=str(score.get("kind") or asset.media_kind),
        token_cost=int(score.get("token_cost") or 0),
        degraded=bool(score.get("degraded")),
        model=score.get("model"),
        extraction=MediaExtractResponse(
            asset_id=asset.id,
            kind=extracted.kind.value,
            text=extracted.text[:20_000],
            features=extracted.features,
            metadata=extracted.metadata,
            pages=extracted.pages,
            tables=extracted.tables,
            warnings=extracted.warnings,
        ),
    )


@router.get("", response_model=list[MediaAssetResponse])
@require_permission(Permission.TASK_READ)
async def list_media(
    request: Request,
    task_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[MediaAssetResponse]:
    """List recent media assets (optionally filtered by task)."""
    actor = _actor(request)
    q = select(MediaAsset).order_by(MediaAsset.created_at.desc()).limit(limit)
    if task_id:
        q = q.where(MediaAsset.task_id == task_id)
    # Light tenancy: non-admin only own when enforced
    from app.core.tenancy import is_admin, tenancy_enforced

    if tenancy_enforced() and not is_admin(actor):
        q = q.where(MediaAsset.created_by == actor)
    rows = (await session.execute(q)).scalars().all()
    return [_asset_to_response(r) for r in rows]


async def _load_asset(session: AsyncSession, asset_id: str) -> MediaAsset:
    result = await session.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise NotFoundError("MediaAsset", asset_id)
    return asset

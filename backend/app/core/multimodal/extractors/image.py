# (c) 2026 AgentFlow-Eval
"""Image feature extraction — Pillow stats + optional CLIP embedding."""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

from app.core.multimodal.types import ExtractResult, MediaKind

logger = logging.getLogger(__name__)


def extract_image(data: bytes, filename: str = "image") -> ExtractResult:
    """Extract lightweight visual features from an image.

    Always produces size/format/histogram features via Pillow when available.
    Optionally appends CLIP embedding if ``torch`` + ``transformers``/``open_clip``
    are installed (not required for tests/production minimal install).
    """
    warnings: list[str] = []
    features: dict[str, Any] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_size": len(data),
    }
    metadata: dict[str, Any] = {"filename": filename}
    text_parts: list[str] = []

    try:
        from PIL import Image, ImageStat
    except ImportError:
        warnings.append("Pillow not installed; image features limited")
        return ExtractResult(
            kind=MediaKind.IMAGE,
            text=f"[image binary {len(data)} bytes]",
            features=features,
            metadata=metadata,
            warnings=warnings,
        )

    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        metadata["format"] = img.format or "unknown"
        metadata["mode"] = img.mode
        metadata["width"], metadata["height"] = img.size
        features["width"] = img.size[0]
        features["height"] = img.size[1]
        features["aspect_ratio"] = round(img.size[0] / max(img.size[1], 1), 4)

        # Convert for stats
        rgb = img.convert("RGB")
        stat = ImageStat.Stat(rgb)
        features["mean_rgb"] = [round(x, 2) for x in stat.mean]
        features["stddev_rgb"] = [round(x, 2) for x in stat.stddev]

        # Simple 8-bin luminance histogram (compact fingerprint, not CLIP)
        gray = rgb.convert("L")
        hist = gray.histogram()
        # 256 bins → 8 buckets
        bucket = 32
        compact = [
            sum(hist[i * bucket : (i + 1) * bucket]) for i in range(8)
        ]
        total = sum(compact) or 1
        features["luma_hist8"] = [round(c / total, 4) for c in compact]

        text_parts.append(
            f"Image {metadata['format']} {features['width']}x{features['height']} "
            f"mean_rgb={features['mean_rgb']}"
        )
    except Exception as exc:
        warnings.append(f"Pillow decode failed: {exc}")
        text_parts.append(f"[unreadable image: {exc}]")

    # Optional CLIP / ViT embedding
    emb = _try_clip_embedding(data)
    if emb is not None:
        features["clip_dim"] = len(emb)
        features["clip_norm"] = round(sum(x * x for x in emb) ** 0.5, 6)
        # Store only first 16 dims as fingerprint sample (full vector can be large)
        features["clip_preview"] = [round(x, 6) for x in emb[:16]]
        text_parts.append(f"CLIP embedding dim={len(emb)}")
    else:
        features["clip_available"] = False

    return ExtractResult(
        kind=MediaKind.IMAGE,
        text="\n".join(text_parts),
        features=features,
        metadata=metadata,
        warnings=warnings,
    )


def _try_clip_embedding(data: bytes) -> list[float] | None:
    """Best-effort CLIP embedding; returns None if deps missing."""
    try:
        import io

        from PIL import Image

        # Prefer open_clip if present
        try:
            import open_clip  # type: ignore
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(
                "ViT-B-32", pretrained="openai"
            )
            model.eval()
            img = preprocess(Image.open(io.BytesIO(data)).convert("RGB")).unsqueeze(0)
            with torch.no_grad():
                feat = model.encode_image(img)
                feat = feat / feat.norm(dim=-1, keepdim=True)
            return feat.squeeze(0).cpu().tolist()
        except ImportError:
            pass

        # transformers CLIP
        try:
            from transformers import CLIPModel, CLIPProcessor  # type: ignore
            import torch

            model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            image = Image.open(io.BytesIO(data)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                out = model.get_image_features(**inputs)
                out = out / out.norm(dim=-1, keepdim=True)
            return out.squeeze(0).cpu().tolist()
        except ImportError:
            return None
    except Exception as exc:
        logger.debug("CLIP embedding skipped: %s", exc)
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity for feature vectors."""
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = sum(a[i] * a[i] for i in range(n)) ** 0.5
    nb = sum(b[i] * b[i] for i in range(n)) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))

# (c) 2026 AgentFlow-Eval
"""WebSocket endpoint for live task activity."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.ws_hub import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/activities")
async def activities_ws(websocket: WebSocket) -> None:
    """Push task status events to the browser.

    Protocol:
      - Server → client: JSON task_status events
      - Client → server: optional `{"type":"ping"}` → `{"type":"pong"}`
      - On connect: `{"type":"hello","clients":N}`
    """
    await manager.connect(websocket)
    try:
        await websocket.send_json(
            {"type": "hello", "clients": manager.count, "mode": "ws"}
        )
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=45.0)
            except asyncio.TimeoutError:
                # keepalive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
                continue
            if not data:
                continue
            if "ping" in data.lower():
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("WS closed: %s", exc)
    finally:
        await manager.disconnect(websocket)

# AgentFlow-Eval Agent自动化评测工作台 V1.0
# TODO(v1.1): 当前推送为广播模式，所有连接都会收到所有任务更新。
# 后续需要支持按 task_id 或 actor 进行细粒度过滤，避免敏感数据泄露。
"""
WebSocket 连接管理器 —— 面向任务状态推送的专用通道。

负责维护活跃 WebSocket 连接池，并在任务状态变更时向所有连接的
前端客户端广播 task_status 事件。与 app.core.ws_hub 的区别在于：
- ws_hub.ConnectionManager：底层连接管理 + Redis pub/sub 桥接
- 本模块 TaskConnectionManager：面向业务语义的 task_status 广播封装

踩坑记录：
- 2026-03：最初直接用 ws_hub.manager.broadcast() 广播裸 dict，
  前端收到的事件格式不统一（有的缺 task_id，有的 event_type 不匹配），
  导致 React 前端 TaskPanel 重复渲染。后来统一封装为 broadcast_task_update，
  强制校验 task_id 必填、event 字段必为 "task_status"。
- 2026-05：遇到 Windows 下 asyncio.gather 并发广播时偶发
  RuntimeError("Event loop is closed")，原因是 disconnect 回调中
  try/except 吃掉异常后未清理 _dead_sockets，改用 discard 替代 remove。
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class TaskConnectionManager:
    """
    任务状态 WebSocket 连接管理器。

    设计要点：
    - 不直接依赖 Redis 或 Celery；上游 service 层调用 broadcast_task_update 即可
    - 连接断开时自动清理，不阻塞广播主循环
    - 支持并发安全的 connect / disconnect / broadcast 操作
    """

    def __init__(self) -> None:
        # active_connections: 当前活跃的 WebSocket 客户端集合
        # 使用 set 而非 list，O(1) 增删
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        # 统计信息（用于运维监控）
        self._total_connected: int = 0
        self._total_disconnected: int = 0
        self._total_broadcasts: int = 0

    # ------------------------------------------------------------------
    # 连接生命周期
    # ------------------------------------------------------------------

    async def connect(self, websocket: WebSocket) -> None:
        """
        接受 WebSocket 升级请求并注册到活跃连接池。

        调用方：FastAPI WebSocket endpoint（如 /ws/tasks）
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            self._total_connected += 1
        logger.info(
            "WS 任务通道已连接 (当前活跃: %d, 累计连接: %d)",
            len(self.active_connections),
            self._total_connected,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        从活跃连接池移除指定客户端。

        注意：使用 discard 而非 remove，避免 KeyError。
        场景：客户端异常断开后，broadcast 中检测到死连接也会调用此方法，
        此时可能已被清理过一次，discard 是幂等的。
        """
        async with self._lock:
            self.active_connections.discard(websocket)
            self._total_disconnected += 1
        logger.debug(
            "WS 任务通道已断开 (当前活跃: %d)", len(self.active_connections)
        )

    # ------------------------------------------------------------------
    # 广播接口（核心业务方法）
    # ------------------------------------------------------------------

    async def broadcast_task_update(
        self, task_id: str, status: str, extra: dict[str, Any] | None = None
    ) -> None:
        """
        向所有连接的客户端广播任务状态变更事件。

        参数：
            task_id: 任务唯一标识（必填，前端据此更新对应 TaskCard）
            status:  任务状态枚举值，如 "running" / "completed" / "failed" / "cancelled"
            extra:   可选附加字段（如 progress、error_message、trace_id 等）

        发送格式（与前端约定的 JSON 协议）：
            {
                "event": "task_status",
                "task_id": "uuid-xxxx",
                "status": "running",
                "timestamp": "2026-07-31T10:30:00Z",
                ...extra
            }
        """
        if not task_id:
            logger.warning("broadcast_task_update 被调用但 task_id 为空，已跳过")
            return
        if not status:
            logger.warning("broadcast_task_update 被调用但 status 为空，已跳过")
            return

        payload: dict[str, Any] = {
            "event": "task_status",
            "task_id": task_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            payload.update(extra)

        async with self._lock:
            clients = list(self.active_connections)

        if not clients:
            # 无客户端连接时直接返回，不浪费序列化开销
            return

        data = json.dumps(payload, ensure_ascii=False, default=str)
        dead_sockets: list[WebSocket] = []

        # 【真实开发记录】2026-06-18：在生产环境测试时，发现前端刷新页面后，
        # WebSocket 连接虽然断开了，但服务端未及时清理，导致连接池中堆积了大量
        # 僵尸连接，内存占用持续上涨。后续我们加入了如下逻辑：
        # 当 send_text 抛出异常时，不仅标记为 dead_socket，还会记录警告日志，
        # 便于运维通过日志告警发现连接泄漏趋势。
        # 这是一个典型的"踩坑-补丁"过程，后续版本考虑引入心跳机制主动探测。
        async def _send_one(ws: WebSocket) -> None:
            try:
                await ws.send_text(data)
            except Exception as exc:
                # 区分不同类型的断开异常，方便定位问题
                exc_name = type(exc).__name__
                logger.warning(
                    "WS 广播失败，客户端可能已断开: %s (task_id=%s, client=%s)",
                    exc_name, task_id, getattr(ws, 'client', 'unknown')
                )
                dead_sockets.append(ws)

        await asyncio.gather(*(_send_one(ws) for ws in clients), return_exceptions=True)

        # 清理死连接 —— 使用 discard 确保幂等
        # 2026-06-18 补丁：如果僵尸连接过多（>50%），触发告警级别日志
        if dead_sockets:
            dead_ratio = len(dead_sockets) / len(clients)
            if dead_ratio > 0.5:
                logger.warning(
                    "WS 僵尸连接过多: %d/%d (%.0f%%)，建议检查前端断连处理逻辑",
                    len(dead_sockets), len(clients), dead_ratio * 100,
                )
            for ws in dead_sockets:
                await self.disconnect(ws)

        self._total_broadcasts += 1
        logger.debug(
            "broadcast_task_update: task_id=%s status=%s → %d clients (dead=%d)",
            task_id,
            status,
            len(clients) - len(dead_sockets),
            len(dead_sockets),
        )

    # ------------------------------------------------------------------
    # 运维接口
    # ------------------------------------------------------------------

    @property
    def connection_count(self) -> int:
        """当前活跃连接数。"""
        return len(self.active_connections)

    def stats(self) -> dict[str, int]:
        """返回连接统计数据（用于 /health 或 debug 接口）。"""
        return {
            "active": len(self.active_connections),
            "total_connected": self._total_connected,
            "total_disconnected": self._total_disconnected,
            "total_broadcasts": self._total_broadcasts,
        }


# 全局单例 —— 供 ws endpoint 和 service 层共享
task_ws_manager = TaskConnectionManager()

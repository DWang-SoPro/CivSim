"""WebSocket 连接管理与流式叙事转发。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from backend.api.sessions import sessions

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


class WebSocketHub:
    """按 game_id 管理进程内 WebSocket 连接。"""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(game_id, set()).add(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(game_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(game_id, None)

    async def broadcast(self, game_id: str, message: dict[str, Any]) -> None:
        """向一局的全部已连接客户端发送 JSON 帧。"""
        dead: list[WebSocket] = []
        for websocket in tuple(self._connections.get(game_id, ())):
            try:
                await websocket.send_json(message)
            except Exception:  # 单个断线不应中断叙事生成
                logger.debug("WebSocket 发送失败，移除连接", exc_info=True)
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(game_id, websocket)

    def connection_count(self, game_id: str) -> int:
        """返回当前游戏的连接数，便于测试和诊断。"""
        return len(self._connections.get(game_id, ()))


ws_hub = WebSocketHub()


@router.websocket("/api/game/{game_id}/ws")
async def game_websocket(websocket: WebSocket, game_id: str) -> None:
    """保持单局游戏的叙事推送连接。"""
    session = sessions.get(game_id)
    if session is None:
        await websocket.accept()
        await websocket.send_json(
            {
                "type": "narrative_error",
                "turn": 0,
                "stream_id": None,
                "payload": {"message": "游戏不存在"},
            }
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_hub.connect(game_id, websocket)
    try:
        while True:
            # MVP 不需要客户端指令；持续 receive 用于感知断线。
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_hub.disconnect(game_id, websocket)

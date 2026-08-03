"""进程内游戏会话存储。

MVP 阶段不做持久化：每局保存当前文明状态、记忆库和串行化回合的锁。
应用重启或多 worker 部署时，这些数据不会在进程间共享。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

from backend.memory.store import MemoryStore
from backend.models.schemas import CivState

GameStatus = Literal["active", "game_over", "awaiting_clarification"]


@dataclass
class GameSession:
    """单局游戏在进程内的全部会话状态。"""

    game_id: str
    state: CivState
    store: MemoryStore
    seed: int
    status: GameStatus = "active"
    game_over_reason: str | None = None
    finalization_error: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    background_tasks: set[asyncio.Task[Any]] = field(
        default_factory=set,
        repr=False,
    )

    def next_rng_seed(self) -> int:
        """返回当前回合的可复现种子。

        回合号只由核心结算推进，因此模糊短路不会消耗种子。
        """
        return self.seed + self.state.turn

    def track_background_task(self, task: asyncio.Task[Any]) -> None:
        """持有后台回合任务的强引用，完成后自动移除。"""
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)


class SessionRegistry:
    """进程内会话注册表。"""

    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}

    def add(self, session: GameSession) -> None:
        """注册一局新游戏。"""
        self._sessions[session.game_id] = session

    def get(self, game_id: str) -> GameSession | None:
        """按 ID 获取会话，不存在时返回 None。"""
        return self._sessions.get(game_id)

    def clear(self) -> None:
        """清空会话，仅供测试与开发重置使用。"""
        self._sessions.clear()

    def __len__(self) -> int:
        return len(self._sessions)


sessions = SessionRegistry()

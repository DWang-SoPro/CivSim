"""进程内游戏会话存储。

MVP：内存会话 + SQLite 存档（见 backend.persistence.saves）。
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
    # 存档 / 终局统计
    autosave_id: str | None = None
    opening_narrative: str | None = None
    year_start: float = 0.0
    initial_population: int = 0
    peak_population: int = 0
    peak_territory: int = 0
    rebellion_streak: int = 0
    elite_collapse_streak: int = 0

    def __post_init__(self) -> None:
        if self.year_start == 0.0:
            self.year_start = self.state.year
        if self.initial_population == 0:
            self.initial_population = self.state.population
        if self.peak_population == 0:
            self.peak_population = self.state.population
        if self.peak_territory == 0:
            self.peak_territory = (
                self.state.territory_core + self.state.territory_frontier
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

    def update_peaks(self) -> None:
        """根据当前状态刷新峰值统计。"""
        self.peak_population = max(self.peak_population, self.state.population)
        territory = self.state.territory_core + self.state.territory_frontier
        self.peak_territory = max(self.peak_territory, territory)

    def update_danger_streaks(self) -> None:
        """更新叛乱/精英瓦解连续计数（供 Game Over 判定）。"""
        tension = (
            self.state.class_tension
            if self.state.class_tension is not None
            else max(0.0, (100.0 - self.state.stability) / 100.0 * 0.7 + 0.15)
        )
        if tension > 0.8 and self.state.stability < 20:
            self.rebellion_streak += 1
        else:
            self.rebellion_streak = 0

        cohesion = (
            self.state.elite_cohesion
            if self.state.elite_cohesion is not None
            else max(0.0, self.state.authority / 100.0 * 0.6 + 0.2)
        )
        if cohesion < 0.15:
            self.elite_collapse_streak += 1
        else:
            self.elite_collapse_streak = 0


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

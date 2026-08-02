"""记忆存储：内存实现（镜像 turns / summaries / landmarks 表结构）。

本阶段手动测试与管线默认走内存库；PostgreSQL 读写可在后续阶段替换
同一接口，无需改 recent / summary / landmark / retriever 调用方。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TurnRecord:
    """对应 turns 表一行（含叙事检索常用派生字段）。"""

    game_id: str
    turn: int
    year_start: float
    year_end: float
    player_input: str
    action_description: str
    result_tier: str
    dimension_changes: dict[str, str]
    narrative: str
    summary: str
    domain_tags: list[str]
    llm_intent: Any = None
    action_result: Any = None
    state_before: Optional[dict[str, Any]] = None
    state_after: Optional[dict[str, Any]] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class SummaryRecord:
    """对应 summaries 表一行。"""

    game_id: str
    turn_start: int
    turn_end: int
    year_start: float
    year_end: float
    content: str
    domain_frequencies: dict[str, int]
    id: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class LandmarkRecord:
    """对应 landmarks 表一行（含预留 embedding 字段）。"""

    game_id: str
    turn: int
    year: float
    tags: list[str]
    title: str
    summary: str
    state_snapshot: dict[str, Any]
    importance_score: int = 1
    embedding: Optional[list[float]] = None
    embedding_model: Optional[str] = None
    id: Optional[int] = None
    created_at: datetime = field(default_factory=_utcnow)


class MemoryStore:
    """单局游戏的内存记忆库。"""

    def __init__(self, game_id: str | None = None) -> None:
        self.game_id = game_id or str(uuid4())
        self._turns: list[TurnRecord] = []
        self._summaries: list[SummaryRecord] = []
        self._landmarks: list[LandmarkRecord] = []
        self._turn_seq = 0
        self._summary_seq = 0
        self._landmark_seq = 0

    # ---- turns ----

    def add_turn(self, record: TurnRecord) -> TurnRecord:
        """追加一轮完整记录。"""
        if record.game_id != self.game_id:
            raise ValueError("turn.game_id 与 store.game_id 不一致")
        self._turn_seq += 1
        stored = copy.deepcopy(record)
        stored.id = self._turn_seq
        self._turns.append(stored)
        self._turns.sort(key=lambda t: t.turn)
        return stored

    def get_recent_turns(self, limit: int = 5) -> list[TurnRecord]:
        """按回合号降序取最近 limit 条，再按升序返回（时间正序）。"""
        ordered = sorted(self._turns, key=lambda t: t.turn, reverse=True)
        recent = ordered[:limit]
        recent.reverse()
        return copy.deepcopy(recent)

    def get_turns_in_range(self, turn_start: int, turn_end: int) -> list[TurnRecord]:
        """闭区间 [turn_start, turn_end] 内的回合。"""
        rows = [t for t in self._turns if turn_start <= t.turn <= turn_end]
        rows.sort(key=lambda t: t.turn)
        return copy.deepcopy(rows)

    def get_all_turns(self) -> list[TurnRecord]:
        return copy.deepcopy(sorted(self._turns, key=lambda t: t.turn))

    # ---- summaries ----

    def add_summary(self, record: SummaryRecord) -> SummaryRecord:
        if record.game_id != self.game_id:
            raise ValueError("summary.game_id 与 store.game_id 不一致")
        self._summary_seq += 1
        stored = copy.deepcopy(record)
        stored.id = self._summary_seq
        self._summaries.append(stored)
        self._summaries.sort(key=lambda s: s.turn_end)
        return stored

    def get_recent_summaries(self, limit: int = 3) -> list[SummaryRecord]:
        ordered = sorted(self._summaries, key=lambda s: s.turn_end, reverse=True)
        recent = ordered[:limit]
        recent.reverse()
        return copy.deepcopy(recent)

    # ---- landmarks ----

    def add_landmark(self, record: LandmarkRecord) -> LandmarkRecord:
        if record.game_id != self.game_id:
            raise ValueError("landmark.game_id 与 store.game_id 不一致")
        self._landmark_seq += 1
        stored = copy.deepcopy(record)
        stored.id = self._landmark_seq
        self._landmarks.append(stored)
        return stored

    def query_landmarks_by_tags(
        self,
        tags: list[str],
        *,
        limit: int = 5,
    ) -> list[LandmarkRecord]:
        """关键词标签重叠检索：tags && query_tags，按 importance_score、turn 降序。"""
        tag_set = {t.lower() for t in tags if t}
        if not tag_set:
            return []
        matched = [
            lm
            for lm in self._landmarks
            if tag_set & {t.lower() for t in lm.tags}
        ]
        matched.sort(key=lambda lm: (lm.importance_score, lm.turn), reverse=True)
        return copy.deepcopy(matched[:limit])

    def get_all_landmarks(self) -> list[LandmarkRecord]:
        return copy.deepcopy(
            sorted(self._landmarks, key=lambda lm: lm.turn)
        )

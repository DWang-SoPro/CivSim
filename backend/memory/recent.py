"""近期记忆管理（最近 5 轮完整记录）。第一阶段占位。"""

from __future__ import annotations


class RecentMemory:
    """近期记忆管理器占位。"""

    def __init__(self) -> None:
        self._turns: list[dict] = []

    def add(self, turn_record: dict) -> None:
        """追加一轮记录。"""
        self._turns.append(turn_record)
        self._turns = self._turns[-5:]

    def get_recent(self) -> list[dict]:
        """返回最近记录。"""
        return list(self._turns)

"""中期摘要管理（第 6—30 轮，每 5 轮一条）。第一阶段占位。"""

from __future__ import annotations


class SummaryMemory:
    """中期摘要管理器占位。"""

    def __init__(self) -> None:
        self._summaries: list[dict] = []

    def add(self, summary: dict) -> None:
        """追加一条摘要。"""
        self._summaries.append(summary)

    def get_recent(self, limit: int = 5) -> list[dict]:
        """返回最近若干条摘要。"""
        return self._summaries[-limit:]

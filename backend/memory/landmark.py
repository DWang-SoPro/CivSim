"""长期关键事件索引管理。第一阶段占位。"""

from __future__ import annotations


class LandmarkMemory:
    """长期索引管理器占位。"""

    def __init__(self) -> None:
        self._landmarks: list[dict] = []

    def add(self, landmark: dict) -> None:
        """追加一条长期索引。"""
        self._landmarks.append(landmark)

    def query_by_tags(self, tags: list[str], limit: int = 5) -> list[dict]:
        """按主题标签检索。"""
        tag_set = set(tags)
        matched = [lm for lm in self._landmarks if tag_set & set(lm.get("tags", []))]
        return matched[-limit:]

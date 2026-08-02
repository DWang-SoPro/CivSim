"""被动事件生成（第一阶段占位）。

后续阶段：按时间跨度触发自然灾害、疫病、边境冲突、继承事件等。
"""

from __future__ import annotations

from typing import Any

from backend.models.schemas import CivState


def check_passive_events(
    state: CivState,
    turn_years: float,
) -> list[dict[str, Any]]:
    """检查并返回本回合被动事件列表。第一阶段返回空列表。"""
    _ = (state, turn_years)
    return []

"""Game Over 检查（第一阶段占位）。

后续阶段实现：大规模叛乱失控、精英瓦解、文明崩溃（文档第八节）。
"""

from __future__ import annotations

from typing import Optional

from backend.models.schemas import CivState


def check_game_over(state: CivState) -> Optional[str]:
    """若触发 Game Over 则返回原因代码，否则返回 None。"""
    if state.population <= 0:
        return "civilization_collapse"
    return None

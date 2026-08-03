"""Game Over 检查（设计文档第八节，MVP 简化版）。

三种死法：叛乱失控 / 精英瓦解 / 文明崩溃。
连续回合追踪由会话侧传入可选计数；无计数时按即时阈值判定。
"""

from __future__ import annotations

from typing import Optional

from backend.models.schemas import CivState


def _class_tension(state: CivState) -> float:
    if state.class_tension is not None:
        return float(state.class_tension)
    # 粗估：稳定与统治力越低，张力越高
    return max(0.0, min(1.0, (100.0 - state.stability) / 100.0 * 0.7 + 0.15))


def _elite_cohesion(state: CivState) -> float:
    if state.elite_cohesion is not None:
        return float(state.elite_cohesion)
    return max(0.0, min(1.0, state.authority / 100.0 * 0.6 + 0.2))


def check_game_over(
    state: CivState,
    *,
    initial_population: int | None = None,
    rebellion_streak: int = 0,
    elite_collapse_streak: int = 0,
) -> Optional[str]:
    """若触发 Game Over 则返回原因代码，否则返回 None。

    返回码：
    - rebellion_out_of_control（叛乱失控）
    - elite_collapse（精英瓦解）
    - civilization_collapse（文明崩溃）
    """
    if state.population <= 0:
        return "civilization_collapse"

    if initial_population and initial_population > 0:
        if state.population < max(1, int(initial_population * 0.1)):
            return "civilization_collapse"

    tension = _class_tension(state)
    if tension > 0.8 and state.stability < 20:
        # 本回合已超标时计入连续轮次（调用方传入的是回合开始前的计数）
        if rebellion_streak + 1 >= 2 or (state.stability < 10 and state.authority < 25):
            return "rebellion_out_of_control"

    cohesion = _elite_cohesion(state)
    if cohesion < 0.15:
        if elite_collapse_streak + 1 >= 2 or state.authority < 20:
            return "elite_collapse"

    # 极端即时崩溃：统治彻底崩盘
    if state.stability <= 5 and state.authority <= 10 and state.population > 0:
        return "rebellion_out_of_control"

    return None


REASON_LABELS: dict[str, str] = {
    "rebellion_out_of_control": "叛乱失控",
    "elite_collapse": "精英瓦解",
    "civilization_collapse": "文明崩溃",
}


def reason_label(reason: str) -> str:
    return REASON_LABELS.get(reason, reason)

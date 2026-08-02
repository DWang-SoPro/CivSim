"""统治力模型（设计文档 §3.5）。

authority_delta =
    + 成功行动的统治力增益
    - 失败行动的统治力损失
    + 3 × (elite_cohesion - 0.5)
    - 5 × max(class_tension - 0.6, 0)
    - 2 × (bureaucratization < 0.2 时的衰减)
"""

from __future__ import annotations

import math


def compute_authority_delta(
    elite_cohesion: float,
    class_tension: float,
    bureaucratization: float,
    action_authority_delta: float = 0.0,
) -> float:
    """计算本回合统治力变化量。

    文档：「bureaucratization < 0.2 时的衰减」按固定 -2 解释
    （即该项贡献为 -2，当且仅当官僚化 < 0.2）。
    """
    low_bureau_penalty = 2.0 if bureaucratization < 0.2 else 0.0
    delta = (
        action_authority_delta
        + 3.0 * (elite_cohesion - 0.5)
        - 5.0 * max(class_tension - 0.6, 0.0)
        - low_bureau_penalty
    )
    if math.isnan(delta) or math.isinf(delta):
        return 0.0
    return delta


def apply_authority(authority: float, delta: float) -> float:
    """应用统治力变化并钳制到 [0, 100]。"""
    result = authority + delta
    if math.isnan(result) or math.isinf(result):
        return max(0.0, min(100.0, authority))
    return max(0.0, min(100.0, result))

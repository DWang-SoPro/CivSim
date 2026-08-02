"""稳定性模型（设计文档 §3.4）。

stability_delta =
    +5 × (food_surplus_ratio - 1.0)
  + 3 × (legitimacy_total - 0.5)
  - 10 × max(class_tension - 0.5, 0)
  - 5 × max(0.5 - elite_cohesion, 0)
  + action_stability_delta
"""

from __future__ import annotations

import math


def compute_stability_delta(
    food_surplus_ratio: float,
    legitimacy_total: float,
    class_tension: float,
    elite_cohesion: float,
    action_stability_delta: float = 0.0,
) -> float:
    """计算本回合稳定性变化量。"""
    delta = (
        5.0 * (food_surplus_ratio - 1.0)
        + 3.0 * (legitimacy_total - 0.5)
        - 10.0 * max(class_tension - 0.5, 0.0)
        - 5.0 * max(0.5 - elite_cohesion, 0.0)
        + action_stability_delta
    )
    if math.isnan(delta) or math.isinf(delta):
        return 0.0
    return delta


def apply_stability(stability: float, delta: float) -> float:
    """应用稳定性变化并钳制到 [0, 100]。"""
    result = stability + delta
    if math.isnan(result) or math.isinf(result):
        return max(0.0, min(100.0, stability))
    return max(0.0, min(100.0, result))

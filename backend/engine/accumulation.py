"""路径积累值更新（设计文档第六节）。

行动贡献：accumulations[domain] += 0.2 × success_weight
自然衰减：每轮 × 0.95
制度化支撑可部分抵消衰减。
"""

from __future__ import annotations

import math
from typing import Optional

from backend.models.schemas import Accumulations, ActionResultTier, CivState

SUCCESS_WEIGHT = {
    ActionResultTier.GREAT_SUCCESS: 1.5,
    ActionResultTier.SUCCESS: 1.0,
    ActionResultTier.PARTIAL: 0.5,
    ActionResultTier.FAILURE: 0.1,
    ActionResultTier.DISASTER: 0.0,
}

DOMAIN_FIELDS = (
    "academic",
    "military",
    "commercial",
    "administrative",
    "cultural",
)

# 行动域 → 积累域映射（MVP）
ACTION_DOMAIN_TO_ACCUMULATION = {
    "economic": "commercial",
    "political": "administrative",
    "military": "military",
    "cultural": "cultural",
    "technology": "academic",
    "composite": "administrative",
}


def success_weight(tier: ActionResultTier) -> float:
    """返回结果档位对应的成功权重。"""
    return SUCCESS_WEIGHT[tier]


def apply_action_contribution(
    accumulations: Accumulations,
    domain: str,
    tier: ActionResultTier,
) -> Accumulations:
    """对指定积累域施加一次行动贡献：+0.2 × success_weight。"""
    field = ACTION_DOMAIN_TO_ACCUMULATION.get(domain, domain)
    if field not in DOMAIN_FIELDS:
        return accumulations.model_copy()

    data = accumulations.model_dump()
    data[field] = max(0.0, data[field] + 0.2 * success_weight(tier))
    return Accumulations(**data)


def apply_natural_decay(
    accumulations: Accumulations,
    *,
    has_academy: bool = False,
    bureaucratization: float = 0.0,
) -> Accumulations:
    """每轮自然衰减 ×0.95，并应用制度化抵消。

    文档：
      academic + has_academy → ×1.03（部分抵消）
      administrative + bureaucratization > 0.5 → ×1.02
    注意：文档写法是先 ×0.95 再 ×1.03/1.02。
    """
    data = accumulations.model_dump()
    for field in DOMAIN_FIELDS:
        value = data[field] * 0.95
        if field == "academic" and has_academy:
            value *= 1.03
        if field == "administrative" and bureaucratization > 0.5:
            value *= 1.02
        if math.isnan(value) or math.isinf(value):
            value = 0.0
        data[field] = max(0.0, value)
    return Accumulations(**data)


def apply_accumulation_turn(
    accumulations: Accumulations,
    *,
    action_domain: Optional[str] = None,
    tier: Optional[ActionResultTier] = None,
    has_academy: bool = False,
    bureaucratization: float = 0.0,
) -> Accumulations:
    """完整一回合积累值更新：行动贡献 + 自然衰减。"""
    result = accumulations
    if action_domain is not None and tier is not None:
        result = apply_action_contribution(result, action_domain, tier)
    return apply_natural_decay(
        result,
        has_academy=has_academy,
        bureaucratization=bureaucratization,
    )


def accumulation_mod(relevant_accumulation: float) -> float:
    """行动成功率修正：1.0 + relevant × 0.3，最高 1.3。"""
    return 1.0 + min(max(relevant_accumulation, 0.0), 1.0) * 0.3


def apply_accumulation_from_state(
    state: CivState,
    *,
    action_domain: Optional[str] = None,
    tier: Optional[ActionResultTier] = None,
    has_academy: bool = False,
) -> Accumulations:
    """从 CivState 更新积累值。"""
    return apply_accumulation_turn(
        state.accumulations,
        action_domain=action_domain,
        tier=tier,
        has_academy=has_academy,
        bureaucratization=state.bureaucratization,
    )

"""社会摩擦模型：行动成功率计算（设计文档 §3.1）。

P_success = P_base × authority_mod × infrastructure_mod × accumulation_mod × random_factor

P_base = 0.8 × (1 - cognitive_gap × resistance / A_norm)
resistance = 0.3×(1-bureaucratization) + 0.3×class_tension
           + 0.2×(1-elite_cohesion) + 0.2×religious_resistance
A_norm = max(统治力 / 20, 0.5)
"""

from __future__ import annotations

import math
import random
from typing import Mapping, Optional

from backend.models.schemas import ActionResultTier, CivState, DecisionStructure

# 成功率区间 → 各档位概率（大成功/成功/部分成功/失败/灾难）
RESULT_TABLE: list[tuple[float, tuple[float, float, float, float, float]]] = [
    # (P_success 下限, (great, success, partial, failure, disaster))
    (0.8, (0.20, 0.50, 0.25, 0.05, 0.00)),
    (0.6, (0.10, 0.35, 0.35, 0.15, 0.05)),
    (0.4, (0.05, 0.20, 0.35, 0.30, 0.10)),
    (0.2, (0.00, 0.10, 0.25, 0.45, 0.20)),
    (0.0, (0.00, 0.05, 0.15, 0.40, 0.40)),
]

EFFECT_MULTIPLIER = {
    ActionResultTier.GREAT_SUCCESS: 1.5,
    ActionResultTier.SUCCESS: 1.0,
    ActionResultTier.PARTIAL: 0.5,
    ActionResultTier.FAILURE: 0.0,
    ActionResultTier.DISASTER: -1.0,  # 负面效果，由调用方解释
}

AUTHORITY_MOD = {
    DecisionStructure.AUTOCRACY: 1.0,
    DecisionStructure.COUNCIL: 0.8,
    DecisionStructure.OLIGARCHY: 0.9,  # 文档未给出，取中间值
    DecisionStructure.BUREAUCRACY: 0.95,  # 文档未给出，略低于独裁
}


def compute_resistance(
    bureaucratization: float,
    class_tension: float,
    elite_cohesion: float,
    religious_resistance: float = 0.0,
) -> float:
    """计算社会惯性系数 resistance。"""
    r = (
        0.3 * (1.0 - _clamp01(bureaucratization))
        + 0.3 * _clamp01(class_tension)
        + 0.2 * (1.0 - _clamp01(elite_cohesion))
        + 0.2 * _clamp01(religious_resistance)
    )
    return max(0.0, r)


def compute_a_norm(authority: float) -> float:
    """归一化统治力 A_norm = max(统治力 / 20, 0.5)。"""
    return max(authority / 20.0, 0.5)


def compute_p_base(
    cognitive_gap: float,
    resistance: float,
    authority: float,
) -> float:
    """计算 P_base = 0.8 × (1 - cognitive_gap × resistance / A_norm)。

    按文档字面公式计算；极端输入下可为负。
    设计意图：最终 P_success 钳制到 [0, 1]。
    """
    a_norm = compute_a_norm(authority)
    return 0.8 * (1.0 - cognitive_gap * resistance / a_norm)


def compute_p_success(
    cognitive_gap: float,
    bureaucratization: float,
    class_tension: float,
    elite_cohesion: float,
    authority: float,
    decision_structure: DecisionStructure,
    infrastructure_mod: float = 1.0,
    accumulation_mod: float = 1.0,
    religious_resistance: float = 0.0,
    random_factor: float = 1.0,
    prerequisites_met: bool = True,
) -> float:
    """计算行动成功率 P_success，钳制到 [0.0, 1.0]。

    Args:
        cognitive_gap: LLM 判断的认知代差 0—5
        infrastructure_mod: 治理效率 × 前置条件满足度
        accumulation_mod: 1.0 + 相关积累值 × 0.3（最高 +30%）
        random_factor: 随机修正，文档范围 0.85—1.15；测试时固定为 1.0
        prerequisites_met: 若不满足，infrastructure_mod 视为 0（行动不可执行）
    """
    if not prerequisites_met:
        infrastructure_mod = 0.0

    resistance = compute_resistance(
        bureaucratization, class_tension, elite_cohesion, religious_resistance
    )
    p_base = compute_p_base(cognitive_gap, resistance, authority)
    authority_mod = AUTHORITY_MOD.get(decision_structure, 1.0)

    # 积累修正上限：+30% → accumulation_mod ≤ 1.3
    accumulation_mod = min(max(accumulation_mod, 0.0), 1.3)
    infrastructure_mod = max(0.0, infrastructure_mod)
    random_factor = max(0.0, random_factor)

    p = p_base * authority_mod * infrastructure_mod * accumulation_mod * random_factor

    if math.isnan(p) or math.isinf(p):
        return 0.0
    # 设计意图：钳制到 [0, 1]（字面乘积在高积累修正下可 >1，极端代差下可 <0）
    return _clamp01(p)


def compute_p_success_from_state(
    state: CivState,
    cognitive_gap: float,
    *,
    infrastructure_mod: float = 1.0,
    relevant_accumulation: float = 0.0,
    religious_resistance: float = 0.0,
    random_factor: float = 1.0,
    prerequisites_met: bool = True,
    class_tension: Optional[float] = None,
    elite_cohesion: Optional[float] = None,
) -> float:
    """从 CivState 计算成功率。"""
    ct = class_tension if class_tension is not None else (state.class_tension or 0.3)
    ec = elite_cohesion if elite_cohesion is not None else (state.elite_cohesion or 0.5)
    accumulation_mod = 1.0 + min(relevant_accumulation, 1.0) * 0.3
    return compute_p_success(
        cognitive_gap=cognitive_gap,
        bureaucratization=state.bureaucratization,
        class_tension=ct,
        elite_cohesion=ec,
        authority=state.authority,
        decision_structure=state.polity.decision_structure,
        infrastructure_mod=infrastructure_mod,
        accumulation_mod=accumulation_mod,
        religious_resistance=religious_resistance,
        random_factor=random_factor,
        prerequisites_met=prerequisites_met,
    )


def result_probabilities(p_success: float) -> Mapping[ActionResultTier, float]:
    """按 P_success 查表，返回各档位概率。"""
    p = _clamp01(p_success)
    for threshold, probs in RESULT_TABLE:
        if p >= threshold:
            tiers = [
                ActionResultTier.GREAT_SUCCESS,
                ActionResultTier.SUCCESS,
                ActionResultTier.PARTIAL,
                ActionResultTier.FAILURE,
                ActionResultTier.DISASTER,
            ]
            return dict(zip(tiers, probs))
    # 不可达；防御性返回最低档
    return {
        ActionResultTier.GREAT_SUCCESS: 0.0,
        ActionResultTier.SUCCESS: 0.05,
        ActionResultTier.PARTIAL: 0.15,
        ActionResultTier.FAILURE: 0.40,
        ActionResultTier.DISASTER: 0.40,
    }


def roll_result_tier(
    p_success: float,
    rng: Optional[random.Random] = None,
) -> ActionResultTier:
    """按成功率查表掷骰，返回结果档位。"""
    probs = result_probabilities(p_success)
    tiers = list(probs.keys())
    weights = list(probs.values())
    r = rng or random.Random()
    return r.choices(tiers, weights=weights, k=1)[0]


def effect_multiplier(tier: ActionResultTier) -> float:
    """结果档位对应的效果倍率。"""
    return EFFECT_MULTIPLIER[tier]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
